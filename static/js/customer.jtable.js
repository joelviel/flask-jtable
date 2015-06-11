


    $(document).ready(function () {
        
        function api_url(model, jtParams) {
            
            return jtParams ? '/' + model + '?' + jtParams.jtStartIndex + '&jtPageSize=' + jtParams.jtPageSize + '&jtSorting=' + jtParams.jtSorting : '/' + model;
        }

        $('#CustomerTableContainer').jtable({
            title: 'Clients',
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
                                $dfd.resolve(data);
                            },
                            error: function () {
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
                    width: '20%'
                },
                first_name: {
                    title: 'Prénom',
                    width: '20%'
                },
                income: {
                    title: 'Revenu en €',
                    width: '20%'
                }
            }
        });

        // Télécharger les données au chargement de la page pour peupler le tableau
        $('#CustomerTableContainer').jtable('load');
    });
