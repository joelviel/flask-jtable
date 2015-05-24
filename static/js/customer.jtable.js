
    $(document).ready(function () {
        $('#CustomerTableContainer').jtable({
            title: 'Clients',
            actions: {
                listAction: '/read/customers',
                createAction: '/create/customer',
                updateAction: '/update/customer',
                deleteAction: '/delete/customer'
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
