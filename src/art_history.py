#!/usr/bin/env python
# encoding: utf-8
"""

Eric Swidler     ejs296
HW 6            

movie_service.py: a RESTful movie data service

"""
import os
import codecs
import json
import re
import urlparse

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("movies", default="../data/movies.csv", help="movies data file")
define("actors", default="../data/actors.csv", help="actors data file")
define("mappings", default="../data/movie_actors.csv", help="key mapping file")

### Movie Web Service implementation ###

class ArtHistory(tornado.web.Application):
    """The Movie Service Web Application"""
    def __init__(self, db):
        favicon_path = '/templates/static/favicon.ico'
        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), "templates/static"),
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            jquery_path=os.path.join(os.path.dirname(__file__), "templates"),
            #Not really working well, will change back to true later
            debug=False,
            autoescape=None,
        )
        
        handlers = [
            #Default Home map
            (r"/", HomeHandler),
            
            #Urls for REST retrieval of data
            (r"/paintings(\..+)?", AllPaintingsHandler),
            (r"/paintings/([0-9]+)(\..+)?", PaintingHandler), 
            (r"/paintings/([0-9]+)/location(\..+)?", PaintingHandler),
            
            #Urls for Application's queries to the server
            (r"/pointUpdate(\..+)?", PointUpdateHandler),
            
            #Urls for painting info updation, new paintings, painting deletetion, etc
            #(r"/pointUpdate(\..+)?", PointUpdateHandler),
           #(r"/pointUpdate(\..+)?", PointUpdateHandler),
            #(r"/pointUpdate(\..+)?", PointUpdateHandler),
            
            #Urls for css, jss, and support files
            (r"/(css/[0-9a-zA-Z]+\.css)", CSSHandler),
            (r"/(js/[0-9a-zA-Z\.\-\/\_]+.png)", tornado.web.StaticFileHandler, dict(path=settings['jquery_path'])),
            (r"/js/([0-9a-zA-Z\.\-\/\_]+)(\.js)", JQueryHandler),
            (r"/(js/[0-9a-zA-Z\.\-\/\_]+\.css)", CSSHandler),
            (r"/([0-9a-zA-Z\.\-\/\_]+.[ico|png])", tornado.web.StaticFileHandler, dict(path=settings['static_path'])),
            
        ]
        
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = db
        print "Webservice Started..."
        
class BaseHandler(tornado.web.RequestHandler):
    """Functions common to all handlers"""
    @property
    def db(self):
        return self.application.db
        
    @property
    def base_uri(self):
        """Returns the Web service's base URI (e.g., http://localhost:8888)"""
        protocol = self.request.protocol
        host = self.request.headers.get('Host')
        return protocol + "://" + host
        
    def write_error(self, status_code, **kwargs):
        """Attach human-readable msg to error messages"""
        self.finish("Error %d - %s" % (status_code, kwargs['message']))
    

class HomeHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "text/html")
        baseHTML = codecs.open('templates/ArtHistory.html', 'r', encoding='utf-8')
        self.write(baseHTML.read())
        #self.write("<html><body><h1>Art History</h1><p>just an example of outputting html</p></body></html>")

#Gets info on all paintings
#Check here for paramaters for range and mediums
class AllPaintingsHandler(BaseHandler):
    def get(self):
        pass
    
#Gets info on specific painting
class PaintingHandler(BaseHandler):
    def get(self, paintingID, format):
        if format == ".json":
            exampleDict = {'success': True, 'image': 'http://images.wikia.com/central/images/e/eb/250px-Mona_Lisa,_by_Leonardo_da_Vinci,_from_C2RMF_retouched.jpg'}
            self.write(exampleDict)
            
    
class CSSHandler(BaseHandler):
    def get(self, fileName):
        self.set_header("Content-Type", "text/css")
        baseHTML = codecs.open("templates/" + fileName, 'r', encoding='utf-8')
        self.write(baseHTML.read())
    
class JQueryHandler(BaseHandler):
    def get(self, fileName, format):
        fileName = fileName + format
        
        if format == ".js":
            self.set_header("Content-Type", "text/javascript")
        elif format == ".css":
            self.set_header("Content-Type", "text/css")
            
        baseHTML = codecs.open("templates/js/" + fileName, 'r', encoding='utf-8')
        self.write(baseHTML.read())
    
class PointUpdateHandler(BaseHandler):
    def get(self, format):
        
        yearRange = self.request.arguments.get("yearRange[]")
        mediums = self.request.arguments.get("mediums[]")
        
        print "Year range " + str(yearRange)
        print "Medium of Pieces " + str(mediums)
        
        responceDict = {'success':False, 'pieces':[], 'error':""}
        self.set_header("Content-Type", "application/json")
        
        if yearRange is None or mediums is None:
            responceDict["error"] = "Incorrect GET arguments provided"
            
            
        else:
            """Need new set of points, their geocoordinates, painting ID, and possibly medium for
            map coloration purposes """
            
            pieces = []
            
            examplePiece1 = {'id':27, 'lat':47.02, 'lng':83.5, 'medium':'oil'}
            examplePiece2 = {'id':19, 'lat':30.02, 'lng':26.5, 'medium':'pastel'}
            examplePiece3 = {'id':83, 'lat':65.02, 'lng':73.5, 'medium':'gesso'}
            
            pieces.append(examplePiece1)
            pieces.append(examplePiece2)
            pieces.append(examplePiece3)
            
            examplePiece21 = {'id':19, 'lat':31.02, 'lng':26.5, 'medium':'pastel'}
            examplePiece22 = {'id':19, 'lat':29.02, 'lng':26.5, 'medium':'pastel'}
            examplePiece23 = {'id':19, 'lat':30.02, 'lng':25.5, 'medium':'pastel'}
            pieces.append(examplePiece21)
            pieces.append(examplePiece22)
            pieces.append(examplePiece23)
            
            if len(pieces) > 0:
                responceDict["pieces"] = pieces
                responceDict["success"] = True
            
        self.write(responceDict)
        
            
#UC1: Retrieve a list of all actors
class ActorListHandler(BaseHandler):
    def get(self, format):
        actors = self.db.list_actors(self.base_uri, None)
        if format is None:
            self.redirect("/actors.json")
        elif format == ".xml":
            self.set_header("Content-Type", "application/xml")
            self.render("actor_list.xml", actors=actors)
        elif format == ".json":
            self.write(dict(actors=actors))
        else:
            self.write_error(401, message="Format %s not supported" % format)
            


### A dummy in-memory database implementation; feel free to reuse it or
### implement your own

class MovieDatabase(object):
    """A dummy in-memory database for handling movie data."""
    def __init__(self, movies_csv, actors_csv, mapping_csv):
        print "Loading data into memory...."
        '''mapping_data = self.read_from_csv(mapping_csv)
        movie_data = self.read_from_csv(movies_csv)
        actor_data = self.read_from_csv(actors_csv)
        self.movies = {}
        for movie in movie_data:
            self.movies[movie['id']] = movie
            actors = [actor['actor_id'] for actor in mapping_data
                            if actor['movie_id'] == movie['id']]
            self.movies[movie['id']]['actors'] = actors
        self.actors = {}
        for actor in actor_data:
            self.actors[actor['id']] = actor
            movies = [movie['movie_id'] for movie in mapping_data
                            if movie['actor_id'] == actor['id']]
            self.actors[actor['id']]['movies'] = movies'''
        
    # ACTOR CRUD operations
    
    def list_actors(self, base_uri, movie_id):
        """Returns a list of actors with IDs converted to URIs"""
        if movie_id is None:
            actors = self.actors.values()
        else:
            actors = [actor for actor in self.actors.values()
                            if movie_id in actor['movies']]
        
            
        actor_list = []
        for actor in actors:
            entry = {}
            entry['uri'] = base_uri + "/actors/" + actor['id']
            if actor.has_key('name'):
                entry['name'] = actor['name']
            actor_list.append(entry)
        return actor_list
    
    
    # Data import
    
    def read_from_csv(self, csv_file):
        """Reads CSV entries into a list containing a set of dictionaries.
        CSV header row entries are taken as dictionary keys"""
        data = []
        with codecs.open(csv_file, 'r', encoding='utf-8') as csvfile:
            header = None
            for i, line in enumerate(csvfile):
                line_split = [x.strip() for x in line.split("|")]
                line_data = [x for x in line_split if len(x) > 0]
                if i == 0:
                    header = line_data
                else:
                    entry = {}
                    for i,datum in enumerate(line_data):
                        entry[header[i]] = datum
                    data.append(entry)
        print "Loaded %d entries from %s" % (len(data), csv_file)
        return data
                    
### Script entry point ###

def main():
    tornado.options.parse_command_line()
    # Set up the database
    db = MovieDatabase(options.movies, options.actors, options.mappings)
    # Set up the Web application, pass the database
    art_webservice = ArtHistory(db)
    # Set up HTTP server, pass Web application
    try:
        http_server = tornado.httpserver.HTTPServer(art_webservice)
        http_server.listen(options.port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print "\nStopping service gracefull..."
    finally:
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
    main()