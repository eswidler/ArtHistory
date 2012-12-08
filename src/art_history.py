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
        handlers = [
            (r"/", HomeHandler),
            (r"/actors(\..+)?", HomeHandler),
            (r"/movies(\..+)?", HomeHandler),
            (r"/actors/([0-9]+)(\..+)?", HomeHandler),
            (r"/movies/([0-9]+)(\..+)?", HomeHandler)
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            debug=True,
            autoescape=None,
        )
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
        self.write(codecs.open('templates/world.html', 'r', encoding='utf-8'))
        #self.write("<html><body><h1>Art History</h1><p>should be a paragraph</p></body></html>")

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