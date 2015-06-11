#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from google.appengine.api import users
from google.appengine.ext import ndb
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

app.jinja_env.line_statement_prefix = '#'


# Modèle de données
class Customer(ndb.Model):
    last_name   = ndb.StringProperty()
    first_name  = ndb.StringProperty()
    income      = ndb.IntegerProperty()

# Les clés des entités ndb doivent être encodées pour faire la réponse AJAX (sinon jsonify retourne une erreur)
# Cette fonction encode les clés d'une liste d'entités


def encode_key(entity):
    return dict(entity.to_dict(), **dict(key=entity.key.urlsafe()))

def encode_keys(entities):
    return [dict(e.to_dict(), **dict(key=e.key.urlsafe())) for e in entities]

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

# Fontion qui renvoie la vue index à l'utilisateur
@app.route('/', methods=['GET'])
def index():

    # Récupération des données concernant l'utilisteur via l'API Google users
    user        = users.get_current_user()
    login_url   = users.create_login_url('/')
    logout_url  = users.create_logout_url('/')

    return render_template('index.html', **locals())


# Definition of CRUD operation foth the model 'Customer'
@app.route('/customers', methods=['GET', 'POST', 'PUT', 'REMOVE'])
def customers():
    
    logging.info("hello customers")
    logging.info(request.method)

    if request.method == "GET" :

        # On récupère l'ensemble des records depuis le Datastore
        customers = Customer.query().fetch()
        
        return jsonify(Result='OK', Records=encode_keys(customers))

    if request.method == "POST" :

        new_customer = form_to_entity(request.form, Customer())
        new_customer.put()
        
        return jsonify(Result='OK', Record=encode_key(new_customer))

    if request.method == "PUT" :

        customer = decode_safekey(request.form['key']).get()
        customer = form_to_entity(request.form, customer)
        customer.put()

        return jsonify(Result='OK')

    # if i use 'DELETE' method, the request does not enter the function customers
    # no idea why it triggers this error

    if request.method == "REMOVE" :

        logging.info("hello delete")

        decode_safekey(request.form['key']).delete()
        
        return jsonify(Result='OK')

    resp = jsonify(Result="ERROR",  Message="Bad Request")
    resp.status_code = 400
    return resp