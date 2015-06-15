


    $(document).ready(function () {
        
        function api_url(model, jtParams) {
            
            return jtParams ? '/' + model + '?' + jtParams.jtStartIndex + '&jtPageSize=' + jtParams.jtPageSize + '&jtSorting=' + jtParams.jtSorting : '/' + model;
        }

        function urlParamsToJson(urlParams){
            return JSON.parse('{"' + decodeURI(urlParams).replace(/"/g, '\\"').replace(/&/g, '","').replace(/=/g,'":"') + '"}');
        }


        $('#CustomerTableContainer').jtable({
            title: 'Clients',
            sorting: true,
            defaultSorting: 'last_name ASC',

            toolbar: {
                items: [{
                    icon: '/img/reset.png',
                    text: 'Reset',
                    click: function () {
                        window.location.href = '/reset_ndb';
                    }
                }]
            },


            actions: {
                
                listAction: function (postData, jtParams) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: api_url('customers', jtParams),
                            type: 'GET',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },
                
                createAction: function (postData, jtParams) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: api_url('customers', jtParams),
                            type: 'POST',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                
                                if (data.Redirect) {
                                    sessionStorage.pendingAction = 'addRecord';
                                    sessionStorage.pendingRecord = JSON.stringify(urlParamsToJson(postData));
                                    window.location.href = data.Redirect;
                                    return
                                }

                                $dfd.resolve(data);
                            },
                            error: function (data) {
                                $dfd.reject();
                            }
                        });
                    });
                },

                updateAction: function(postData, jtParams) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: api_url('customers', jtParams),
                            type: 'PUT',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {

                                if (data.Redirect) {
                                    sessionStorage.pendingAction = 'updateRecord';
                                    sessionStorage.pendingRecord = JSON.stringify(urlParamsToJson(postData));
                                    window.location.href = data.Redirect;
                                    return
                                }


                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },
                


                deleteAction: function(postData) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: api_url('customers'),
                            type: 'REMOVE',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                if (data.Redirect) {
                                    sessionStorage.pendingAction = 'deleteRecord';
                                    // différent des opérations CU
                                    sessionStorage.pendingRecordKey = postData.key;
                                    window.location.href = data.Redirect;
                                    return
                                }

                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },


            },
            fields: {
                key: {
                    key: true,
                    list: false
                },
                last_name: {
                    title: 'Nom',
                    width: '20%',
                    display: function (data) {
                        return '<a href="/customers/'+ data.record.key +'">' + data.record.last_name + '</a>';
                    }

                },
                first_name: {
                    title: 'Prénom',
                    width: '20%'
                },
                income: {
                    title: 'Revenu en €',
                    width: '20%'
                }
            },


            recordsLoaded: function(event, data) {
                if (sessionStorage.pendingAction && Number(sessionStorage.loggedUser)) {
        
                    var options = sessionStorage.pendingAction == 'deleteRecord' ?
                        // bug avec deleteRecord, elle n'utilisera pas l'url indiquée dans deleteAction, donc besoin de l'indiquer ici 
                        {key:sessionStorage.pendingRecordKey, url:'/customers'} :
                        {record:JSON.parse(sessionStorage.pendingRecord)}

                    $('#CustomerTableContainer').jtable(sessionStorage.pendingAction, options);
                }
                sessionStorage.clear();
            }
        })


        // Télécharger les données au chargement de la page pour peupler le tableau
        $('#CustomerTableContainer').jtable('load');

        //Re-load records when user click 'load records' button.
        $('#LoadRecordsButton').click(function (e) {
            e.preventDefault();
            $('#CustomerTableContainer').jtable('load', {
                last_name:  $('#last-name').val()
            });
        });

        
    });
