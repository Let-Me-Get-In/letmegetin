==========
Places API
==========

This API defines the available endpoints for operations on accessible places referenced on `jaccede.com <http://www.jaccede.com/>`_.

.. note::

 All responses are wrapped in a json object with at most 2 attributes:
  * status: One of *OK*, *NOK* or *NO_RESULTS*
  * results: The results as described in the documentation below. Could be missing, depending on the status.

Search places
=============

Dev
 GET http://dev.jaccede.com/api/places/search/

Prod
 GET http://api3.jaccede.com/v3/places/search/

**PARAMETERS** (All optional)

**category_id**
    Id for the category.

**what**
    Name or type of place.

**where**
    Location information such as city name, zipcode, street name and country.

**country**
    2-letter ISO 639-1 language code. http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    You can see available country using :ref:`ref-available-country`

**longitude**
    If both longitude and latitude are specified, it becomes a **proximity search** and the **where**
    parameter is **ignored**.

**latitude**
    See longitude

**offset**
    Default is 0

**page**
    You can use it instead of offset. It will generate an offset = limit * page
    For example, page=2 with limit=10 correspond to offset=20
    Default is 0.


**limit**
    Default is 10

**lang**
    2-letter ISO 639-1 language code. Default is *French (fr)*. Possible values: **fr**, **en**, **de**, or **es**.

**EXAMPLES**

    Search for a bar in paris
    http://dev.jaccede.com/api/places/search/?what=bar&where=paris

**RESPONSE**
 Example response (a json object) for request http://dev.jaccede.com/api/places/search/?where=paris&what=bar+sportif&limit=1

::


    {
      "status": "OK",
      "total_found": 2,
      "query_offset": 0,
      "query_lang": "fr",
      "query_limit": 1,
      "results": [
        {
          "website": null,
          "category": {
            "list_icon_filename": "RESTAUBAR_Bars-Cafes.png",
            "group_id": "7",
            "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/RESTAUBAR_Bars-Cafes.png",
            "name": "Bars / Caf\u00e9s",
            "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_RESTAUBAR_Bars-Cafes.png",
            "group_name": "Restauration / Bars",
            "id": "1",
            "map_icon_filename": "RESTAUBAR_Bars-Cafes.png"
          },
          "description": "Bar \"Sportif\" (Foot-Rugby)-Tabac-Brasserie-Pub\n\nLa hauteur du comptoir (bar + caisse tabac) est de 110 cm. L'entr\u00e9e/sortie sont facilement rep\u00e9rables (l'entr\u00e9e accessible n'est pas celle visualis\u00e9e sur la photo, elle se situe plus \u00e0 gauche). Il n'y a pas d'\u00e9quipement particulier de pr\u00e9vu pour les autres handicaps.",
          "edit_date": "2013-09-18T11:20:21.561Z",
          "creator": {
            "pseudo": "jeremdev",
            "avatar_url_full": null,
            "uid": "jeremdev",
            "avatar_url_thumb": null
          },
          "name": "L'Ambroisie",
          "distance_from_poi": null,
          "telephone": "01 43 59 54 80",
          "full_address": "21, Rue du Colis\u00e9e PARIS 75008 (fr)",
          "creation_date": "2011-05-27T18:25:11Z",
          "media": [
            {
              "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/94e5c9da58c43cd5f23a6c25b852a851.jpg",
              "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/94e5c9da58c43cd5f23a6c25b852a851.jpg"
            }
          ],
          "total_comments": 1,
          "total_photos": 1,
          "address": {
            "city_name": "paris",
            "latitude": 48.8709,
            "country_code": "fr",
            "city_zipcode": "75008",
            "longitude": 2.30873
          },
          "accessibility_rating": 7,
          "reception_rating": 4,
          "uid": "0k6-lambroisie-paris"
        }
      ]
    }

Fetch place details
===================

Dev
 GET http://dev.jaccede.com/api/places/<place_uid>/

Prod
 GET http://api3.jaccede.com/v3/places/<place_uid>/

**PARAMETERS** (All optional)

**lang**
 2-letter ISO 639-1 language code. Default is *French (fr)*.

 Possible values: **fr**, **en**, **de**, or **es**.


**EXAMPLES**

 http://dev.jaccede.com/api/places/0qs-nimporte-quoi-paris/



**Response**: A json object

For rating, please use the rating attribute and not accessibility_rating and reception_rating

::

 {
  "results": {
    "accessibility": [
      {
        "criteria": [
          {
            "criterion": {
              "description": null,
              "id": 1,
              "name": "Access",
              "subtype": "multichoice_single_value",
              "type": "multichoice"
            },
            "values": [
              {
                "option": {
                  "description": "Small step, maximum 2cm ",
                  "id": 4,
                  "label": "Low raised entrance",
                  "precision_label": null,
                  "value": "Low raised entrance"
                },
                "precision": null
              }
            ]
          },
          {
            "criterion": {
              "description": "Wide opening",
              "id": 3,
              "name": "Door width (cm)",
              "type": "user_value"
            },
            "value": "Normale (= 80 cm)"
          }
        ],
        "description": null,
        "id": 1,
        "name": "ENTRANCE"
      },
      {
        "criteria": [
          {
            "criterion": {
              "description": null,
              "id": 7,
              "name": "Wheelchair access to all areas",
              "subtype": "multichoice_single_value",
              "type": "multichoice"
            },
            "values": [
              {
                "option": {
                  "description": "E.g. some areas are only accessible by stairs",
                  "id": 16,
                  "label": "Some areas are not accessible to wheelchair users",
                  "precision_label": null,
                  "value": "Partial accessibility"
                },
                "precision": null
              }
            ]
          }
        ],
        "description": null,
        "id": 2,
        "name": "MOBILITY"
      },
      {
        "criteria": [
          {
            "criterion": {
              "description": null,
              "id": 16,
              "name": "Restrooms",
              "subtype": "multichoice_single_value",
              "type": "multichoice"
            },
            "values": [
              {
                "option": {
                  "description": null,
                  "id": 37,
                  "label": "Restrooms inaccessible",
                  "precision_label": null,
                  "value": "Inaccessible"
                },
                "precision": null
              }
            ]
          },
          {
            "criterion": {
              "description": null,
              "id": 26,
              "name": "Furnishings and equipment",
              "subtype": "multichoice_multiple_values",
              "type": "multichoice"
            },
            "values": [
              {
                "option": {
                  "description": "Can be moved to facilitate use or clear space.",
                  "id": 53,
                  "label": "Movable equipment and/or furnishings",
                  "precision_label": null,
                  "value": "Movable "
                },
                "precision": null
              }
            ]
          }
        ],
        "description": null,
        "id": 3,
        "name": "SERVICES AND FACILITIES"
      }
    ],
    "accessibility_rating": 5,
    "accessible_by_conviction": false,
    "address": {
      "city_name": "PARIS",
      "city_zipcode": "75001",
      "country_code": "fr",
      "latitude": 48.8608000000,
      "longitude": 2.3438100000,
      "street_name": "16 rue Roule"
    },
    "category": {
      "group_id": 7,
      "group_name": "Restaurants / Bars",
      "id": 1,
      "list_icon_filename": "RESTAUBAR_Bars-Cafes.png",
      "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_RESTAUBAR_Bars-Cafes.png",
      "map_icon_filename": "RESTAUBAR_Bars-Cafes.png",
      "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/RESTAUBAR_Bars-Cafes.png",
      "name": "Bars/coffee shops"
    },
    "comments": [
      {
        "accessibility_rating": 6,
        "body": "Ambiance et patron sympa, la musique est parfois un peu forte\r\nEntr\u00e9e facile\r\nPiste au sous-sol inaccessible \u00e0 cause de l'escalier mais le reste du bar est ok\r\nLes toilettes ne sont pas am\u00e9nag\u00e9es et \u00e9troites mais de plein-pied",
        "commentor": {
          "avatar_url_full": null,
          "avatar_url_thumb": null,
          "profile": {
            "id": 1,
            "name": "Person with limited mobility"
          },
          "pseudo": "Stephane G",
          "uid": "seigneurcaradoc"
        },
        "creation_date": "Thu, 01 Mar 2007 14:53:21 GMT",
        "rating": 4,
        "reception_rating": 8,
        "title": "N'importe quoi"
      },
      {
        "accessibility_rating": 4,
        "body": "Ambiance jeune (\u00e9tudiante) et cocktails extravagants. ",
        "commentor": {
          "avatar_url_full": "http://cdn1.jaccede.net/uploads/users/imgs/full/damien5.jpg",
          "avatar_url_thumb": "http://cdn1.jaccede.net/uploads/users/imgs/thumbs/damien5.jpg",
          "profile": {
            "id": 1,
            "name": "Person with limited mobility"
          },
          "pseudo": "Damienb",
          "uid": "damienb"
        },
        "creation_date": "Sun, 02 Jul 2006 17:10:49 GMT",
        "rating": 3,
        "reception_rating": 8,
        "title": "Commentaire du cr\u00e9ateur de la fiche"
      }
    ],
    "create_lang": "fr",
    "creation_date": "Sun, 02 Jul 2006 17:10:49 GMT",
    "creator": {
      "avatar_url_full": "http://cdn1.jaccede.net/uploads/users/imgs/full/damien5.jpg",
      "avatar_url_thumb": "http://cdn1.jaccede.net/uploads/users/imgs/thumbs/damien5.jpg",
      "profile": {
        "id": 1,
        "name": "Person with limited mobility"
      },
      "pseudo": "Damienb",
      "uid": "damienb"
    },
    "description": "L'int\u00e9rieur est petit mais. Seul le RDC est praticable.",
    "edit_date": "Wed, 18 Sep 2013 10:40:37 GMT",
    "email": null,
    "full_address": "16 rue Roule PARIS 75001 (fr)",
    "hours": null,
    "id": 9,
    "is_favorite": false,
    "media": [
      {
        "description": "Pic 1 for place N'importe Quoi",
        "filename": "Image 1.png",
        "name": "Pic 1 for place N'importe Quoi",
        "tag": "default",
        "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/Image 1.png",
        "type": "image",
        "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/Image 1.png"
      },
      {
        "description": "Pic 2 for place N'importe Quoi",
        "filename": "34493131c0eb03d2a4b8ecf67d67485c.jpg",
        "name": "Pic 2 for place N'importe Quoi",
        "tag": "default",
        "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/34493131c0eb03d2a4b8ecf67d67485c.jpg",
        "type": "image",
        "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/34493131c0eb03d2a4b8ecf67d67485c.jpg"
      },
      {
        "description": "Pic 3 for place N'importe Quoi",
        "filename": "9fa2f46a4030effffd4affdb0c6db203.jpg",
        "name": "Pic 3 for place N'importe Quoi",
        "tag": "default",
        "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/9fa2f46a4030effffd4affdb0c6db203.jpg",
        "type": "image",
        "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/9fa2f46a4030effffd4affdb0c6db203.jpg"
      },
      {
        "description": "Pic 4 for place N'importe Quoi",
        "filename": "01fa8aa3a460cf7b5789863ed3cf4e07.jpg",
        "name": "Pic 4 for place N'importe Quoi",
        "tag": "default",
        "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/01fa8aa3a460cf7b5789863ed3cf4e07.jpg",
        "type": "image",
        "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/01fa8aa3a460cf7b5789863ed3cf4e07.jpg"
      }
    ],
    "name": "N'importe Quoi",
    "placegroups": [],
    "rating": 3.0,
    "reception_rating": 8,
    "telephone": "01 40 26 29 71",
    "uid": "0qs-nimporte-quoi-paris",
    "website": "http://www.nimportequoi.fr/"
  },
  "status": "OK"
 }

Create a Place
==============

Dev
 POST http://dev.jaccede.com/api/places/create/

Prod
 POST http://api3.jaccede.com/v3/places/create/


**PARAMETERS** (* Mandatory)

.. note:: This values should be in a json object with the parameter name **place_values**.

**editor_uid** *
 Creator's unique id.

**name** *

**category_id** *

**description** *

**longitude**

**latitude**

**country_code** *

**street_number** *

**street_name** *

**city_name** *

**city_zipcode** *

**phone**

**email**

**website**

**hours**
 Opening hours

**source**
 Default is web. Possible values: *web*, *iphone*, *android*, *blackberry*, *mobile-web*, *other*

**keywords**
 Comma separated values, if several.

**accessibility_rating** *

**reception_rating** *



**accessibility** *

.. warning:: Json array of criteria object


 3 attributes in the accessibility array: *type*, *reception_points* and *criteria* array.

 The criteria array contains, for each criteria:

 * id: The criteria id
 * type: The type: *multichoice* or *user_value*
 * value: If the criteria type is *user_value*, the value entered by the user.
 * values: If the criteria type is *multichoice*, an array of values. Note that in most cases, its only one value unless the criteria's **values_option** attribute (see. accessibility form) has a value of **multiple**.
 * user_precisions: Json object whose key is the **value id**, and the value is the value entered by the user. Multi-choice criteria values can have an attribute *user_can_precise* which means that if a user selects that value, he/she can add supplementary information eg. For an front door criteria, possible values could be no steps, 1 step, several steps. If for the  1 step value, the user can precise, then in this case, the use can, for example, indicate the exact step height.


**Example of data**: A json object

::

 {
       "accessibility" :
           [
            {'id': 1,
              'type': u'multichoice',
              'user_precisions': {u'5': u'5 cm'},
              'values': [5]},
            {'id': 2, 'type': u'multichoice', 'values': [7]},
            {'id': 3,
              'type': u'user_value',
              'value': u'Accessible (> ou = 90 cm)'},
            {'id': 6, 'type': u'multichoice', 'values': [14]},
            {'id': 7, 'type': u'multichoice', 'values': [15]},
            {'id': 26, 'type': u'multichoice', 'values': [60]},
            {'id': 44,
              'type': u'user_value',
              'value': u'plop'},
       ],
       'reception_rating': 9,
       'accessibility_rating': 9,
       "category_id" : 63,
       "city_name" : "Paris",
       "city_zipcode" : "75012",
       "country_code" : "fr",
       "description" : "Desc TestAm",
       "editor_uid" : "amath",
       "name" : "TestAm",
       "source" : "iphone",
       "street_name" : "passage turquetil",
       "street_number" : "10"
   }


**Response**: A json object

::

    {
      "status": "OK",
      "results": {
        "total_found": 2,
        "query_limit": 20,
        "query_offset": 0,
        "favorites": [
          {
            "category": {
              "list_icon_filename": "RESTAUBAR_Bars-Cafes.png",
              "group_id": 7,
              "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/RESTAUBAR_Bars-Cafes.png",
              "name": "Bars / Caf\u00e9s",
              "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_RESTAUBAR_Bars-Cafes.png",
              "group_name": "Restauration / Bars",
              "id": 1,
              "map_icon_filename": "RESTAUBAR_Bars-Cafes.png"
            },
            "placegroups": [],
            "uid": "0y2-tabac-de-leurope-paris",
            "edit_date": "Tue, 14 Apr 2015 11:23:27 GMT",
            "creator": {
              "profile": {
                "name": "Citoyen engag\u00e9",
                "id": 3
              },
              "avatar_url_full": null,
              "pseudo": "cyrano",
              "uid": "cyrano-1am",
              "avatar_url_thumb": null
            },
            "create_lang": "fr",
            "media": [],
            "description": "Bar Tabac",
            "accessibility": [
              {
                "description": null,
                "criteria": [
                  {
                    "values": [
                      {
                        "precision": "8",
                        "option": {
                          "precision_label": "pr\u00e9ciser (en cm)",
                          "description": "Pr\u00e9ciser la hauteur en cm",
                          "value": "1 marche",
                          "label": "1 marche \u00e0 l'entr\u00e9e, hauteur (cm)",
                          "user_can_precise": true,
                          "id": 5
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_single_value",
                      "description": null,
                      "type": "multichoice",
                      "id": 1,
                      "name": "Acc\u00e8s"
                    }
                  },
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 6,
                          "precision_label": "pr\u00e9ciser",
                          "description": null,
                          "value": "Manuelle",
                          "label": "Porte \u00e0 ouverture manuelle"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_single_value",
                      "description": null,
                      "type": "multichoice",
                      "id": 2,
                      "name": "Ouverture de porte"
                    }
                  },
                  {
                    "criterion": {
                      "description": "Largeur utile",
                      "type": "user_value",
                      "id": 3,
                      "name": "Largeur de porte (cm)"
                    },
                    "value": "100"
                  },
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 92,
                          "precision_label": "pr\u00e9ciser",
                          "description": "qc",
                          "value": "oui",
                          "label": "oui"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_binary_value",
                      "description": "L\u2019entr\u00e9e accessible est l\u2019entr\u00e9e principale",
                      "type": "multichoice",
                      "id": 47,
                      "name": "L\u2019entr\u00e9e accessible est l\u2019entr\u00e9e principale"
                    }
                  }
                ],
                "id": 1,
                "name": "ENTR\u00c9E"
              },
              {
                "description": null,
                "criteria": [
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 14,
                          "precision_label": "pr\u00e9ciser",
                          "description": null,
                          "value": "Ais\u00e9e",
                          "label": "Circulation ais\u00e9e dans les all\u00e9es"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_single_value",
                      "description": null,
                      "type": "multichoice",
                      "id": 6,
                      "name": "Circulation dans les all\u00e9es"
                    }
                  },
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 16,
                          "precision_label": "pr\u00e9ciser",
                          "description": "Par exemple : certains espaces ne sont accessibles que par escalier.",
                          "value": "Partiel",
                          "label": "Certains espaces ne sont pas accessibles en fauteuil"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_single_value",
                      "description": null,
                      "type": "multichoice",
                      "id": 7,
                      "name": "Acc\u00e8s en fauteuil \u00e0 tout le lieu"
                    }
                  }
                ],
                "id": 2,
                "name": "CIRCULATION"
              },
              {
                "description": null,
                "criteria": [
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 37,
                          "precision_label": "pr\u00e9ciser",
                          "description": null,
                          "value": "Inaccessibles",
                          "label": "Sanitaires inaccessibles"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_single_value",
                      "description": null,
                      "type": "multichoice",
                      "id": 16,
                      "name": "Sanitaires"
                    }
                  },
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 54,
                          "precision_label": "pr\u00e9ciser",
                          "description": "Sp\u00e9cialement con\u00e7u pour s'adapter \u00e0 certaines d\u00e9ficiences.",
                          "value": "Adapt\u00e9",
                          "label": "Mobilier et/ou \u00e9quipements adapt\u00e9s"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_multiple_values",
                      "description": null,
                      "type": "multichoice",
                      "id": 26,
                      "name": "Mobilier et \u00e9quipements"
                    }
                  }
                ],
                "id": 3,
                "name": "SERVICES ET \u00c9QUIPEMENTS"
              },
              {
                "description": null,
                "criteria": [
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 89,
                          "precision_label": "pr\u00e9ciser",
                          "description": "Trottoirs larges, lisses et d\u00e9gag\u00e9s",
                          "value": "Sans obstacles",
                          "label": "Trottoirs sans obstacles"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_multiple_values",
                      "description": null,
                      "type": "multichoice",
                      "id": 40,
                      "name": "Trottoirs (obstacles)"
                    }
                  },
                  {
                    "values": [
                      {
                        "precision": null,
                        "option": {
                          "id": 80,
                          "precision_label": "pr\u00e9ciser",
                          "description": null,
                          "value": "Oui",
                          "label": "Oui"
                        }
                      }
                    ],
                    "criterion": {
                      "subtype": "multichoice_binary_value",
                      "description": "Enseigne suffisamment visible et lisible",
                      "type": "multichoice",
                      "id": 41,
                      "name": "Enseigne suffisamment visible et lisible"
                    }
                  }
                ],
                "id": 4,
                "name": "EXT\u00c9RIEUR"
              }
            ],
            "full_address": "82, Rue de Miromesnil Paris 75008 (fr)",
            "id": 88996,
            "comments": [],
            "address": {
              "country_code": "fr",
              "street_number": "82",
              "street_name": "Rue de Miromesnil",
              "longitude": 2.3157600000,
              "latitude": 48.8776000000,
              "city_zipcode": "75008",
              "city_name": "Paris"
            },
            "creation_date": "Fri, 10 Apr 2015 16:41:21 GMT",
            "accessibility_rating": 6,
            "reception_rating": 7,
            "name": "Tabac de l'Europe"
          },
          {
            "placegroups": [],
            "edit_date": "Thu, 26 Feb 2015 17:24:39 GMT",
            "media": [],
            "accessibility": [],
            "comments": [],
            "creation_date": "Thu, 26 Feb 2015 17:24:39 GMT",
            "id": 88903
          }
        ]
      }
    }



Update a place
==============

Dev
 POST http://dev.jaccede.com/api/places/<place_uid>/update/

Prod
 POST http://api3.jaccede.com/v3/places/<place_uid>/update/

**Parameters**
 Same as for create place but none is mandatory, except *editor_uid*.

**RESPONSE**: json object
 Same as for crate place

Fetch place comments
====================

Dev
 GET http://dev.jaccede.com/api/places/<place_uid>/comments/

Prod
 GET http://api3.jaccede.com/v3/places/<place_uid>/comments/

**PARAMETERS** (All optional)

**lang**
 2-letter ISO 639-1 language code. Default is *French (fr)*.

 Possible values: **fr**, **en**, **de**, or **es**.

**offset**
 Default is 0

**limit**
 Default is 20

**EXAMPLES**

 http://dev.jaccede.com/api/places/0x2-bar-belushis-cafe-paris/comments/

**RESPONSE**: json object

::

 {
  "status": "OK",
  "results": {
    "total_found": 1,
    "limit": 20,
    "comments": [
      {
        "body": "Etablissement accessible et bien adapt\u00e9 aux personnes \u00e0 mobilit\u00e9 r\u00e9duite.\r\nDans la salle d'acc\u00e8s \u00e0 internet, un poste de travail est adapt\u00e9 aux PMR.\r\nSalle des f\u00eates (night-club) accessible en sous-sol.\r\nTarifs chambre : 20 (dortoir) \u00e0 80 (individuelle) euros.",
        "commentor": {
          "profile": {
            "name": "Citoyen engag\u00e9",
            "id": 3
          },
          "avatar_url_full": null,
          "pseudo": "Journ\u00e9e de l'accessibilit\u00e9 Paris 2009",
          "uid": "journee-de-laccessibilite-paris-2009",
          "avatar_url_thumb": null
        },
        "accessibility_rating": 10,
        "reception_rating": 10,
        "creation_date": "Sat, 14 Nov 2009 16:30:36 GMT"
      }
    ],
    "offset": 0
  }
 }

Add place media
===============

Dev
 POST http://dev.jaccede.com/api/places/<place_uid>/media/add/

Prod
 POST http://api3.jaccede.com/v3/places/<place_uid>/media/add/

**MimeType**
 multipart/form-data

**Parameters**

**editor_uid** *
 User's unique id.

**fobj** *
 Image file object

**RESPONSE**: json object

**EXAMPLES**

http://dev.jaccede.com/api/places/0x2-bar-belushis-cafe-paris/media/add/

::

    {
        "status": "OK",
        "results": {
            'url': u'http://dev.jaccede.com/static/uploads/imgs/test_20150313-0002-9AJ.png',
            'tag': u'default',
            'type': u'image',
            'filename': u'test_20150313-0002-9AJ.png'
        }
    }

Fetch place medias
==================

Dev
 GET http://dev.jaccede.com/api/places/media/

Prod
 GET http://api3.jaccede.com/v3/places/media/

**PARAMETERS** (Optional)

**offset**
 Default is 0

**limit**
 Default is 20

**EXAMPLES**

 http://dev.jaccede.com/api/places/0x2-bar-belushis-cafe-paris/media/

**Response**: json object

::

  {
      "status": "OK",
      "results": {
        "total_found": 5,
        "media": [
          {
            "name": "Pic 1 for place Novotel Tour Eiffel ****",
            "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/5-0034128f41cd5d78a2e087f39179ed21.jpg",
            "filename": "5-0034128f41cd5d78a2e087f39179ed21.jpg",
            "tag": "default",
            "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/5-0034128f41cd5d78a2e087f39179ed21.jpg",
            "type": "image",
            "description": "Pic 1 for place Novotel Tour Eiffel ****"
          },
          {
            "name": "Pic 2 for place Novotel Tour Eiffel ****",
            "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/5-92920176b84bb4a12e85af021fb47ac2.jpg",
            "filename": "5-92920176b84bb4a12e85af021fb47ac2.jpg",
            "tag": "default",
            "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/5-92920176b84bb4a12e85af021fb47ac2.jpg",
            "type": "image",
            "description": "Pic 2 for place Novotel Tour Eiffel ****"
          },
          {
            "name": "Pic 3 for place Novotel Tour Eiffel ****",
            "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/5-2422d6144309b0953520c6e7745eb881.jpg",
            "filename": "5-2422d6144309b0953520c6e7745eb881.jpg",
            "tag": "default",
            "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/5-2422d6144309b0953520c6e7745eb881.jpg",
            "type": "image",
            "description": "Pic 3 for place Novotel Tour Eiffel ****"
          },
          {
            "name": "Pic 4 for place Novotel Tour Eiffel ****",
            "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/4-6e8a968e9a10ce3d320435a4364bede2.jpg",
            "filename": "4-6e8a968e9a10ce3d320435a4364bede2.jpg",
            "tag": "default",
            "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/4-6e8a968e9a10ce3d320435a4364bede2.jpg",
            "type": "image",
            "description": "Pic 4 for place Novotel Tour Eiffel ****"
          },
          {
            "name": "photo Novotel Tour Eiffel ****",
            "url": "http://cdn1.jaccede.net/uploads/places/imgs/full/VZiI49A-img_0490.JPG",
            "filename": "VZiI49A-img_0490.JPG",
            "tag": "default",
            "thumb_url": "http://cdn1.jaccede.net/uploads/places/imgs/thumbs/VZiI49A-img_0490.JPG",
            "type": "image",
            "description": "Chambre d'h\u00f4tel parfaitement accessible !"
          }
        ],
        "limit": 20,
        "offset": 0
      }
    }

Fetch place comments
====================

Dev
 GET http://dev.jaccede.com/api/places/<place_uid>/comments/

Prod
 GET http://api3.jaccede.com/v3/places/<place_uid>/comments/

**QUERY STRING PARAMETERS** (All optional)

**offset**
 Default is 0

**limit**
 Default is 20

**lang**
 2-letter ISO 639-1 language code. Default is *French (fr)*.

 Possible values: **fr**, **en**, **de**, or **es**.

**EXAMPLES**

 http://dev.jaccede.com/api/places/0x2-bar-belushis-cafe-paris/comments/

**Response**: json object

::

 {
  "status": "OK",
  "results": {
    "total_found": 1,
    "limit": 20,
    "comments": [
      {
        "body": "Etablissement accessible et bien adapt\u00e9 aux personnes \u00e0 mobilit\u00e9 r\u00e9duite.\r\nDans la salle d'acc\u00e8s \u00e0 internet, un poste de travail est adapt\u00e9 aux PMR.\r\nSalle des f\u00eates (night-club) accessible en sous-sol.\r\nTarifs chambre : 20 (dortoir) \u00e0 80 (individuelle) euros.",
        "commentor": {
          "profile": {
            "name": "Citoyen engag\u00e9",
            "id": 3
          },
          "avatar_url_full": null,
          "pseudo": "Journ\u00e9e de l'accessibilit\u00e9 Paris 2009",
          "uid": "journee-de-laccessibilite-paris-2009",
          "avatar_url_thumb": null
        },
        "accessibility_rating": 10,
        "reception_rating": 10,
        "creation_date": "Sat, 14 Nov 2009 16:30:36 GMT"
      }
    ],
    "offset": 0
  }
 }





Comment a place
===============

Dev
 POST http://dev.jaccede.com/api/places/<place_uid>/comments/add/

Prod
 POST http://api3.jaccede.com/v3/places/<place_uid>/comments/add/

**PARAMETERS**  (* Mandatory)

**editor_uid** *
 Commentor's unique id.

**title**:
 Comment title

**body**:
 Comment body

**accessibility_rating** (Integer):
 Accessibility points

**reception_rating**:
 Reception points


Fetch place categories (by group)
=================================

Dev
 GET http://dev.jaccede.com/api/places/categories/

Prod
 GET http://api3.jaccede.com/v3/places/categories/

**PARAMETERS** (all optional)

**offset**
 Default is 0

**limit**
 Default is 50

**main_kw_id**
 cf. fetch place main keywords

**lang**
 2-letter ISO 639-1 language code. Default is *French (fr)*.

 Possible values: **fr**, **en**, **de**, or **es**.

**EXAMPLES**
 http://dev.jaccede.com/api/places/categories/?tjx=1&limit=1


**Response**: json object.
::

 {
  "total_found": 1,
  "status": "OK",
  "limit": 1,
  "results": [
    {
      "id": 5,
      "categories": [
        {
          "list_icon_filename": "LOISCULT_Plages.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Plages.png",
          "name": "Plages",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Plages.png",
          "group_name": "Loisirs / Culture",
          "id": 20,
          "map_icon_filename": "LOISCULT_Plages.png"
        },
        {
          "list_icon_filename": "LOISCULT_Cinemas.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Cinemas.png",
          "name": "Cin\u00e9mas",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Cinemas.png",
          "group_name": "Loisirs / Culture",
          "id": 2,
          "map_icon_filename": "LOISCULT_Cinemas.png"
        },
        {
          "list_icon_filename": "LOISCULT_Discotheques.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Discotheques.png",
          "name": "Discoth\u00e8ques",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Discotheques.png",
          "group_name": "Loisirs / Culture",
          "id": 3,
          "map_icon_filename": "LOISCULT_Discotheques.png"
        },
        {
          "list_icon_filename": "LOISCULT_Salles-de-spectacles-concerts.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Salles-de-spectacles-concerts.png",
          "name": "Salles de spectacles / concerts",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Salles-de-spectacles-concerts.png",
          "group_name": "Loisirs / Culture",
          "id": 5,
          "map_icon_filename": "LOISCULT_Salles-de-spectacles-concerts.png"
        },
        {
          "list_icon_filename": "LOISCULT_Parcs-Jardins.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Parcs-Jardins.png",
          "name": "Parcs / Jardins",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Parcs-Jardins.png",
          "group_name": "Loisirs / Culture",
          "id": 7,
          "map_icon_filename": "LOISCULT_Parcs-Jardins.png"
        },
        {
          "list_icon_filename": "LOISCULT_Parcs-attractions.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Parcs-attractions.png",
          "name": "Parcs d'attraction",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Parcs-attractions.png",
          "group_name": "Loisirs / Culture",
          "id": 9,
          "map_icon_filename": "LOISCULT_Parcs-attractions.png"
        },
        {
          "list_icon_filename": "LOISCULT_Bibliotheques-Mediatheques.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Bibliotheques-Mediatheques.png",
          "name": "Biblioth\u00e8ques / M\u00e9diath\u00e8ques",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Bibliotheques-Mediatheques.png",
          "group_name": "Loisirs / Culture",
          "id": 10,
          "map_icon_filename": "LOISCULT_Bibliotheques-Mediatheques.png"
        },
        {
          "list_icon_filename": "LOISCULT_Galeries-art.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Galeries-art.png",
          "name": "Galeries d'art",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Galeries-art.png",
          "group_name": "Loisirs / Culture",
          "id": 11,
          "map_icon_filename": "LOISCULT_Galeries-art.png"
        },
        {
          "list_icon_filename": "LOISCULT_Monuments.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Monuments.png",
          "name": "Monuments",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Monuments.png",
          "group_name": "Loisirs / Culture",
          "id": 12,
          "map_icon_filename": "LOISCULT_Monuments.png"
        },
        {
          "list_icon_filename": "LOISCULT_Musees-Centres-art.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Musees-Centres-art.png",
          "name": "Mus\u00e9es / Centres d'art",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Musees-Centres-art.png",
          "group_name": "Loisirs / Culture",
          "id": 13,
          "map_icon_filename": "LOISCULT_Musees-Centres-art.png"
        },
        {
          "list_icon_filename": "LOISCULT_Operas.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Operas.png",
          "name": "Op\u00e9ras",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Operas.png",
          "group_name": "Loisirs / Culture",
          "id": 14,
          "map_icon_filename": "LOISCULT_Operas.png"
        },
        {
          "list_icon_filename": "LOISCULT_Theatres.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Theatres.png",
          "name": "Th\u00e9\u00e2tres",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Theatres.png",
          "group_name": "Loisirs / Culture",
          "id": 15,
          "map_icon_filename": "LOISCULT_Theatres.png"
        },
        {
          "list_icon_filename": "LOISCULT_Autres.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Autres.png",
          "name": "Loisirs / Culture - Autres",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Autres.png",
          "group_name": "Loisirs / Culture",
          "id": 21,
          "map_icon_filename": "LOISCULT_Autres.png"
        },
        {
          "list_icon_filename": "LOISCULT_Zoos-Aquariums.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Zoos-Aquariums.png",
          "name": "Zoos / Aquariums",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Zoos-Aquariums.png",
          "group_name": "Loisirs / Culture",
          "id": 59,
          "map_icon_filename": "LOISCULT_Zoos-Aquariums.png"
        },
        {
          "list_icon_filename": "LOISCULT_Cirques.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Cirques.png",
          "name": "Cirques",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Cirques.png",
          "group_name": "Loisirs / Culture",
          "id": 61,
          "map_icon_filename": "LOISCULT_Cirques.png"
        },
        {
          "list_icon_filename": "LOISCULT_Casinos.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Casinos.png",
          "name": "Casinos",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Casinos.png",
          "group_name": "Loisirs / Culture",
          "id": 64,
          "map_icon_filename": "LOISCULT_Casinos.png"
        },
        {
          "list_icon_filename": "LOISCULT_Sites-naturels.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Sites-naturels.png",
          "name": "Sites naturels",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Sites-naturels.png",
          "group_name": "Loisirs / Culture",
          "id": 65,
          "map_icon_filename": "LOISCULT_Sites-naturels.png"
        },
        {
          "list_icon_filename": "LOISCULT_Stades.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Stades.png",
          "name": "Stades",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Stades.png",
          "group_name": "Loisirs / Culture",
          "id": 66,
          "map_icon_filename": "LOISCULT_Stades.png"
        },
        {
          "list_icon_filename": "LOISCULT_Bowlings.png",
          "group_id": 5,
          "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/LOISCULT_Bowlings.png",
          "name": "Bowlings",
          "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_LOISCULT_Bowlings.png",
          "group_name": "Loisirs / Culture",
          "id": 121,
          "map_icon_filename": "LOISCULT_Bowlings.png"
        }
      ],
      "name": "Loisirs / Culture"
    }
  ],
  "offset": 0
 }

.. note::

 The main keyword - category relationship is similar to a category - sub category relationship, respectively.

Fetch accessibility form for a given type of place
====================================================

.. note::

 Accessibility criteria forms change depending on the place category.

Dev
 GET http://dev.jaccede.com/api/places/categories/<category_id>/criteria/

Prod
 GET http://api3.jaccede.com/v3/places/categories/<category_id>/criteria/


**EXAMPLES**
 http://dev.jaccede.com/api/places/categories/1/criteria/

**Response**: json array (link above).

::

    {
      "status": "OK",
      "results": {
        "criteria_groups": [
          {
            "description": null,
            "criteria": [
              {
                "is_mandatory": true,
                "description": null,
                "options": [
                  {
                    "id": 1,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Plain-pied",
                    "label": "Acc\u00e8s de plain-pied"
                  },
                  {
                    "precision_label": "pr\u00e9ciser (en cm)",
                    "description": "Pr\u00e9ciser la hauteur en cm",
                    "value": "1 marche",
                    "label": "1 marche \u00e0 l'entr\u00e9e, hauteur (cm)",
                    "user_can_precise": true,
                    "id": 5
                  },
                  {
                    "id": 2,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Rampe",
                    "label": "Acc\u00e8s avec rampe"
                  },
                  {
                    "id": 4,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Petite marche, d'une hauteur maximale de 2 cm.",
                    "value": "Ressaut",
                    "label": "Ressaut \u00e0 l'entr\u00e9e"
                  },
                  {
                    "id": 3,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Ascenseur / \u00e9l\u00e9vateur",
                    "label": "Acc\u00e8s par ascenseur ou \u00e9l\u00e9vateur"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 1,
                "name": "Acc\u00e8s"
              },
              {
                "is_mandatory": true,
                "description": null,
                "options": [
                  {
                    "id": 6,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Manuelle",
                    "label": "Porte \u00e0 ouverture manuelle"
                  },
                  {
                    "id": 7,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Automatique",
                    "label": "Porte \u00e0 ouverture automatique"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 2,
                "name": "Ouverture de porte"
              },
              {
                "is_mandatory": true,
                "description": "Largeur utile",
                "type": "user_value",
                "id": 3,
                "name": "Largeur de porte (cm)"
              },
              {
                "is_mandatory": false,
                "description": null,
                "options": [
                  {
                    "id": 8,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Sur les portes vitr\u00e9es, une bande ou un motif de 5 cm. doit \u00eatre plac\u00e9 \u00e0 une hauteur comprise entre 110 et 160 cm. ",
                    "value": "Absence de marquage sur porte vitr\u00e9e",
                    "label": "Absence de marquage sur porte vitr\u00e9e"
                  },
                  {
                    "id": 9,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Par exemple : porte tr\u00e8s lourde.",
                    "value": "Porte difficile \u00e0 maintenir ouverte",
                    "label": "Porte difficile \u00e0 maintenir ouverte"
                  },
                  {
                    "id": 10,
                    "precision_label": "pr\u00e9ciser",
                    "description": "La conception de la poign\u00e9e rend sa prehension difficile.",
                    "value": "Poign\u00e9e peu ergonomique",
                    "label": "Poign\u00e9e peu ergonomique"
                  }
                ],
                "subtype": "multichoice_multiple_values",
                "type": "multichoice",
                "id": 4,
                "name": "Obstacles \u00e0 la porte d'entr\u00e9e"
              },
              {
                "is_mandatory": false,
                "description": "L\u2019entr\u00e9e accessible est l\u2019entr\u00e9e principale",
                "options": [
                  {
                    "id": 92,
                    "precision_label": "pr\u00e9ciser",
                    "description": "qc",
                    "value": "oui",
                    "label": "oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 47,
                "name": "L\u2019entr\u00e9e accessible est l\u2019entr\u00e9e principale"
              }
            ],
            "id": 1,
            "name": "ENTR\u00c9E"
          },
          {
            "description": null,
            "criteria": [
              {
                "is_mandatory": false,
                "description": null,
                "options": [
                  {
                    "id": 13,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Difficile",
                    "label": "Circulation difficile dans les all\u00e9es"
                  },
                  {
                    "id": 14,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Ais\u00e9e",
                    "label": "Circulation ais\u00e9e dans les all\u00e9es"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 6,
                "name": "Circulation dans les all\u00e9es"
              },
              {
                "is_mandatory": false,
                "description": null,
                "options": [
                  {
                    "id": 15,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Total",
                    "label": "Acc\u00e8s en fauteuil possible partout"
                  },
                  {
                    "id": 16,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Par exemple : certains espaces ne sont accessibles que par escalier.",
                    "value": "Partiel",
                    "label": "Certains espaces ne sont pas accessibles en fauteuil"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 7,
                "name": "Acc\u00e8s en fauteuil \u00e0 tout le lieu"
              },
              {
                "is_mandatory": false,
                "description": "Dimensions de la cabine. (largeur x profondeur)",
                "options": [
                  {
                    "id": 17,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Dimensions de la cabine sup\u00e9rieures \u00e0 100 x 130 cm. (largeur x profondeur)",
                    "value": "Grand",
                    "label": "Ascenseur de grandes dimensions"
                  },
                  {
                    "id": 18,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Dimensions de la cabine d'environ 100 x 130 cm. (largeur x profondeur)",
                    "value": "Standard",
                    "label": "Ascenseur de dimensions suffisantes"
                  },
                  {
                    "id": 19,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Dimensions de la cabine inf\u00e9rieures \u00e0 100 x 130 cm. (largeur x profondeur)",
                    "value": "Petit",
                    "label": "Ascenseur de petites dimensions"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 8,
                "name": "Ascenseurs (dimensions)"
              },
              {
                "is_mandatory": false,
                "description": "Equipements facilitant l'utilisation de l'ascenseur.",
                "options": [
                  {
                    "id": 20,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Annonce vocale des \u00e9tages",
                    "label": "Annonce vocale des \u00e9tages"
                  },
                  {
                    "id": 21,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Chiffres en relief (ou braille)",
                    "label": "Chiffres en relief sur le panneau de commande"
                  },
                  {
                    "id": 22,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Hauteur des boutons et autres commandes comprise entre 90 et 130 cm.",
                    "value": "Commandes \u00e0 hauteur de fauteuil",
                    "label": "Commandes \u00e0 hauteur de fauteuil"
                  }
                ],
                "subtype": "multichoice_multiple_values",
                "type": "multichoice",
                "id": 9,
                "name": "Ascenseurs (Adaptations)"
              }
            ],
            "id": 2,
            "name": "CIRCULATION"
          },
          {
            "description": null,
            "criteria": [
              {
                "is_mandatory": false,
                "description": "Une partie du comptoir doit avoir une hauteur maximale de 80 cm. ou \u00eatre \u00e9quip\u00e9 d'un \u00e9critoire.",
                "options": [
                  {
                    "id": 34,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Oui",
                    "label": "Oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 15,
                "name": "Hauteur adapt\u00e9e des comptoirs / guichets"
              },
              {
                "is_mandatory": true,
                "description": null,
                "options": [
                  {
                    "id": 90,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Non renseign\u00e9",
                    "value": "Non renseign\u00e9",
                    "label": "Sanitaires non renseign\u00e9"
                  },
                  {
                    "id": 37,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Inaccessibles",
                    "label": "Sanitaires inaccessibles"
                  },
                  {
                    "id": 36,
                    "precision_label": "pr\u00e9ciser",
                    "description": "De plain-pied, mais pas am\u00e9nag\u00e9.",
                    "value": "Peu accessibles",
                    "label": "Sanitaires non am\u00e9nag\u00e9s mais de plain-pied"
                  },
                  {
                    "id": 35,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Am\u00e9nag\u00e9s",
                    "label": "Sanitaires am\u00e9nag\u00e9s pour les PMR"
                  }
                ],
                "subtype": "multichoice_single_value",
                "type": "multichoice",
                "id": 16,
                "name": "Sanitaires"
              },
              {
                "is_mandatory": false,
                "description": "Personnel form\u00e9 \u00e0 l'accueil des personnes en situation de handicap",
                "options": [
                  {
                    "id": 48,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Oui",
                    "label": "Oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 21,
                "name": "Personnel form\u00e9 \u00e0 l'accueil des personnes en situation de handicap"
              },
              {
                "is_mandatory": false,
                "description": "Personnel initi\u00e9 \u00e0 la langue des signes",
                "options": [
                  {
                    "id": 49,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Oui",
                    "label": "Oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 22,
                "name": "Personnel initi\u00e9 \u00e0 la langue des signes"
              },
              {
                "is_mandatory": false,
                "description": null,
                "options": [
                  {
                    "id": 54,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Sp\u00e9cialement con\u00e7u pour s'adapter \u00e0 certaines d\u00e9ficiences.",
                    "value": "Adapt\u00e9",
                    "label": "Mobilier et/ou \u00e9quipements adapt\u00e9s"
                  },
                  {
                    "id": 53,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Peuvent \u00eatre d\u00e9plac\u00e9s pour faciliter leur utilisation ou d\u00e9gager l'espace.",
                    "value": "Amovible",
                    "label": "Mobilier et/ou \u00e9quipements amovibles"
                  }
                ],
                "subtype": "multichoice_multiple_values",
                "type": "multichoice",
                "id": 26,
                "name": "Mobilier et \u00e9quipements"
              },
              {
                "is_mandatory": false,
                "description": "Menu en braille",
                "options": [
                  {
                    "id": 55,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Oui",
                    "label": "Oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 27,
                "name": "Menu en braille"
              }
            ],
            "id": 3,
            "name": "SERVICES ET \u00c9QUIPEMENTS"
          },
          {
            "description": null,
            "criteria": [
              {
                "is_mandatory": true,
                "description": null,
                "options": [
                  {
                    "id": 89,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Trottoirs larges, lisses et d\u00e9gag\u00e9s",
                    "value": "Sans obstacles",
                    "label": "Trottoirs sans obstacles"
                  },
                  {
                    "id": 76,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Abaiss\u00e9s = hauteur des trottoirs r\u00e9duite au niveau des passages pi\u00e9tons.",
                    "value": "Sans abaiss\u00e9s",
                    "label": "Trottoirs sans abaiss\u00e9s"
                  },
                  {
                    "id": 77,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Pav\u00e9s \"ronds\" rendant difficiles les d\u00e9placements en fauteuil roulant.",
                    "value": "Pav\u00e9s",
                    "label": "Trottoirs pav\u00e9s"
                  },
                  {
                    "id": 78,
                    "precision_label": "pr\u00e9ciser",
                    "description": "Largeur du trottoir inf\u00e9rieure \u00e0 120 cm.",
                    "value": "\u00c9troits",
                    "label": "Trottoirs \u00e9troits"
                  },
                  {
                    "id": 79,
                    "precision_label": "pr\u00e9ciser",
                    "description": "D\u00e9vers : pente lat\u00e9rale de plus de 2%.",
                    "value": "D\u00e9vers",
                    "label": "Trottoirs en d\u00e9vers"
                  }
                ],
                "subtype": "multichoice_multiple_values",
                "type": "multichoice",
                "id": 40,
                "name": "Trottoirs (obstacles)"
              },
              {
                "is_mandatory": false,
                "description": "Enseigne suffisamment visible et lisible",
                "options": [
                  {
                    "id": 80,
                    "precision_label": "pr\u00e9ciser",
                    "description": null,
                    "value": "Oui",
                    "label": "Oui"
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 41,
                "name": "Enseigne suffisamment visible et lisible"
              },
              {
                "is_mandatory": false,
                "description": "Place de parking public r\u00e9serv\u00e9e aux personnes d\u00e9tentrices d'une carte de stationnement GIG/GIC.",
                "options": [
                  {
                    "precision_label": "pr\u00e9ciser",
                    "description": "Place GIG/GIC \u00e0 proximit\u00e9",
                    "value": "Place GIG/GIC \u00e0 proximit\u00e9",
                    "label": "Place GIG/GIC \u00e0 proximit\u00e9",
                    "user_can_precise": true,
                    "id": 81
                  }
                ],
                "subtype": "multichoice_binary_value",
                "type": "multichoice",
                "id": 42,
                "name": "Place GIG/GIC \u00e0 proximit\u00e9"
              },
              {
                "is_mandatory": false,
                "description": "Proximit\u00e9 d'une station de transport en commun accessible. Par exemple : bus ou tramway accessible et am\u00e9nag\u00e9.",
                "type": "user_value",
                "id": 44,
                "name": "Transports accessibles \u00e0 proximit\u00e9"
              }
            ],
            "id": 4,
            "name": "EXT\u00c9RIEUR"
          }
        ],
        "list_icon_filename": "RESTAUBAR_Bars-Cafes.png",
        "group_id": 7,
        "map_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/map/RESTAUBAR_Bars-Cafes.png",
        "name": "Bars / Caf\u00e9s",
        "list_icon_url": "http://cdn1.jaccede.net/assets/categories/icons/web/list/34x30_RESTAUBAR_Bars-Cafes.png",
        "group_name": "Restauration / Bars",
        "id": 1,
        "map_icon_filename": "RESTAUBAR_Bars-Cafes.png"
      }
    }
