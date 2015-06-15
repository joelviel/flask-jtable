#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging, json, time, requests
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
    address     = ndb.JsonProperty(default=dict(city=None, state=None, street=None, zip=None))
    income      = ndb.IntegerProperty(default=0)
    created     = ndb.DateTimeProperty(auto_now_add=True)
    modified    = ndb.DateTimeProperty(auto_now=True)
    creator     = ndb.UserProperty(default=None)
    photo       = ndb.BlobKeyProperty()
    photo_url   = ndb.StringProperty(default='/img/default.png')
    phone       = ndb.StringProperty()

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

def userApi_to_entity(result, entity):
    
    entity.last_name    = user['name']['last']
    entity.first_name   = user['name']['first']

    entity.address['city']      = user['location']['city']
    entity.address['state']     = user['location']['state']
    entity.address['street']    = user['location']['street']
    entity.address['zip']       = user['location']['state']

    entity.photo_url    = user['picture']['medium']

    entity.phone        = user['phone']
    
    return entity


def file_to_dictList(filename):
    '''Retourne une liste de dicionnaire à partir d'un fichier contenant une liste d'objets JSON'''
    file_data = open('static/json/'+filename, 'r')
    dictList = json.load(file_data)
    file_data.close()
    return dictList


def clear_ndb(cls_name):
    '''Supprime toutes les entités de type cls_name dans la ndb'''
    cls = eval(cls_name.capitalize())
    ndb.delete_multi(cls.query().fetch(keys_only=True))

def get_default_customers():
    '''Use Random User Generator API to get default_customers'''
    url = "http://api.randomuser.me/?results=25"
    headers = {'User-agent': 'Mozilla/5.0'}
    req = requests.get(url, headers=headers)
    return json.loads(req.content)
    #return req.content


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
    '''Fonction qui renvoie la page d'index. 
    Les infos de l'utilisateur sont récupérés via l'API Google users'''

    user        = users.get_current_user()
    login_url   = users.create_login_url('/')
    logout_url  = users.create_logout_url('/')

    return render_template('index.html', **locals())



@app.route('/customers', methods=['GET', 'POST', 'PUT', 'REMOVE'])
@app.route('/customers/<safekey>', methods=['GET', 'POST'])
@login_required_for_CUD
def customers(safekey=None):
    '''Opérer des actions CRUD sur le modèle de données Customer
    CRUD = Create, Read, Update, Delete '''

    if request.method == "GET" :

        if not safekey:
            
            qry_customers = Customer.query(ancestor=ROOT.key)

            # Mauvais idée de faire le tri avec order car on ne peut pas filtrer sur l'attribut 1 et faire un tri sur l'attribut 2
            # ==> ERR:The first sort property must be the same as the property to which the inequality filter is applied.  In your query the first sort property is first_name but the inequality filter is on last_name
            # ==> on tri donc les attributs après le fetch avec la fonction native python sort
            sort = request.args.get('jtSorting')
            # if sort:

            #     if 'ASC' in sort : sort = 'Customer.'  + sort[:-4]
            #     else             : sort = '-Customer.' + sort[:-4]

            #     qry_customers = qry_customers.order(eval(sort))

            # A utiliser plus tard si besoin. On repère toutes les demandes de filtre en repérant les params portant un nom d'attribut
            filters = list(set(request.args.keys()).intersection(dir(Customer())))

            # Filtre uniquement possible sur l'attribut last_name pour le moment
            if 'last_name' in filters and request.args.get('last_name'):
                filter_val_min = request.args.get('last_name')
                filter_val_max = filter_val_min[:-1] + chr(ord(filter_val_min[-1]) + 1)
                logging.info(filter_val_max)
                qry_customers = qry_customers.filter(Customer.last_name >= filter_val_min).filter(Customer.last_name < filter_val_max)

            customers = qry_customers.fetch()

            if sort:
                customers.sort(key=lambda x: getattr(x,sort.split(' ')[0]), reverse='DESC' in sort)

            return jsonify(Result='OK', Records=encode_keys(customers))

        else:
            # Récupération d'une url pour uploader la photo du customer dans le blobstore si besoin
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
            
            if f:
                header = f.headers['Content-Type']
                parsed_header = parse_options_header(header)
                bkey_str = parsed_header[1]['blob-key']
                
                # si le customer a déjà une photo, on supprime le blob exsitant et on stocke la clé du nouveau blob
                if customer.photo:
                    blobstore.delete(customer.photo)
                customer.photo = blobstore.BlobKey(bkey_str)
                customer.put()

            return redirect(request.url)

    elif request.method == "PUT" :

        customer = decode_safekey(request.form['key']).get()
        
        if customer.creator == users.get_current_user() or not customer.creator:
            customer = form_to_entity(request.form, customer)
            customer.put()
            return jsonify(Result='OK')
        
        return jsonify(Result='ERROR', Message="Vous ne pouvez modifier que les valeurs par défaut ou vos crations")


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

@app.route("/tasks/reset_ndb")
@app.route("/reset_ndb")
def reset_ndb():
    start_time = time.time()
    clear_ndb('customer')
    default_customers = file_to_dictList('default_customers.json')
    ndb.put_multi([form_to_entity(d, Customer(parent=ROOT.key, creator=None)) for d in default_customers])
    
    if 'task' in request.url:
        return jsonify(exec_time = time.time() - start_time)

    else:
        return redirect('/')