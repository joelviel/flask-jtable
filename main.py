#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from google.appengine.api import users, app_identity, images
from google.appengine.ext import ndb, blobstore
from flask import Flask, render_template, jsonify, request, redirect, make_response
from functools import wraps
from werkzeug.http import parse_options_header


app = Flask(__name__)

app.jinja_env.line_statement_prefix = '#'

#logging.info(app_identity.get_service_account_name())

########################
# Le Modèle de données #
########################

# Pour assurer un fetch consitant lors d'une query, il est nécessaire d'affecter un parent à chaque entité
# Le risque est sinon de ne pas récupérer lors du fetch une entité fraichement sauvegardée dans la ndb
# C'est aussi nécessaire pour faire des transactions (opérations atomiques)
# cf. https://cloud.google.com/appengine/docs/python/datastore/structuring_for_strong_consistency
# cf. https://cloud.google.com/appengine/docs/python/ndb/transactions
class Root(ndb.Model): pass
ROOT =  Root.get_or_insert(app_identity.get_application_id())

class Customer(ndb.Model):
    last_name   = ndb.StringProperty(validator=lambda p, v: v.capitalize() or '-')
    first_name  = ndb.StringProperty(validator=lambda p, v: v.capitalize() or '-')
    income      = ndb.IntegerProperty(default=0)
    created     = ndb.DateTimeProperty(auto_now_add=True)
    modified    = ndb.DateTimeProperty(auto_now=True)
    creator     = ndb.UserProperty(required=True)
    photo       = ndb.BlobKeyProperty()

#############
# Fonctions #
#############


# Les clés des entités ndb doivent être encodées pour faire une réponse AJAX (sinon jsonify retourne une erreur)

def encode_keys(entities):
    return [dict(e.to_dict(exclude=['creator', 'created', 'modified', 'photo']), **dict(key=e.key.urlsafe())) for e in entities]

def encode_key(entity):
    return encode_keys([entity])[0]

def decode_safekey(safekey):
    return ndb.Key(urlsafe=safekey)

def form_to_entity(form, entity):
    
    for key, value in form.iteritems():

        # La clé d'un record n'est pas considérée
        if key == 'key'     : continue
        
        # Le champs income doit contenir un nombre (integer). Dans le cas contraire, on fixe la valeur à 0
        if key == 'income'  : 
            try: value = int(value)
            except ValueError: value = 0
        
        setattr(entity, key, value)
    
    return entity



###############
# Décorateurs #
###############


def login_required_for_CUD(f):
    '''L'utilisateur doit être connecté pour opérer les actions Create, Update et Delete
    Sinon il est redirigé vers la page de login'''

    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = users.get_current_user()
        if not current_user and request.method != 'GET':
            return jsonify(Result="OK",  Redirect=users.create_login_url())
        return f(*args, **kwargs)
    return decorated_function



###############
# Contrôleurs #
###############


@app.route('/')
def index():
    '''Fontion qui renvoie la page d'index. 
    Les infos de l'utilisateur sont récupérés via l'API Google users'''

    user        = users.get_current_user()
    login_url   = users.create_login_url('/')
    logout_url  = users.create_logout_url('/')

    ROOT =  Root.get_or_insert(app_identity.get_application_id())

    #root_photo = ROOT.

    return render_template('index.html', **locals())



@app.route('/customers', methods=['GET', 'POST', 'PUT', 'REMOVE'])
@app.route('/customers/<safekey>', methods=['GET', 'POST'])
@login_required_for_CUD
def customers(safekey=None):
    '''Opérer des actions CRUD sur le modèle de données Customer
    CRUD = Create, Read, Update, Delete '''

    if request.method == "GET" :

        if not safekey:
            customers = Customer.query(ancestor=ROOT.key).fetch()
            return jsonify(Result='OK', Records=encode_keys(customers))

        else:
            upload_url = blobstore.create_upload_url('/customers/'+safekey)
            customer = decode_safekey(safekey).get()
            if customer.photo :
                customer_photo =  images.get_serving_url(customer.photo, size=128, crop=False, secure_url=None)
            return render_template('customer-details.html', **locals())

    elif request.method == "POST" :

        if not safekey:
            new_customer = form_to_entity(request.form, Customer(parent=ROOT.key, creator=users.get_current_user()))
            new_customer.put()
            return jsonify(Result='OK', Record=encode_key(new_customer))

        else:
            
            customer = decode_safekey(safekey).get()
            f = request.files['file']

            logging.info('hello file')
            
            if f:
                header = f.headers['Content-Type']
                parsed_header = parse_options_header(header)
                bkey_str = parsed_header[1]['blob-key']
                
                if customer.photo:
                    blobstore.delete(customer.photo)

                customer.photo = blobstore.BlobKey(bkey_str)
                customer.put()
            return redirect(request.url)

    elif request.method == "PUT" :

        customer = decode_safekey(request.form['key']).get()
        customer = form_to_entity(request.form, customer)
        customer.put()

        return jsonify(Result='OK')

    # Bug si utilisation de la méthode DELETE (la route n'est pas trouvée)
    elif request.method == "REMOVE" :
        
        decode_safekey(request.form['key']).delete()
        
        return jsonify(Result='OK')

    else:
        resp = jsonify(Result="ERROR",  Message="Bad Request")
        resp.status_code = 400
        return resp


@app.route("/img/<bkey>")
def img(bkey):
    
    blob_info = blobstore.get(bkey)
    response = make_response(blob_info.open().read())
    response.headers['Content-Type'] = blob_info.content_type
    return response