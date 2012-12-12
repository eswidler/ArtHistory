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
import urllib

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
    
    def get_format(self):
        #returns format for redirect from accept header
        mappings= {"text/html":".html","application/json":".json","application/xml":".xml","text/turtle":".ttl"}
        accept= self.request.headers['Accept']
        for format in mappings:
            if format in accept:
                return mappings[format]
        return ""
        
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
class AllPaintingsHandler(BaseHandler):
    def get(self,format):
        paintings= self.db.list_paintings(self.base_uri)
        mappings= {".html":"text/html",".xml":"application/xml",".ttl":"text/turtle"}
        if format is None:
            fmt= self.get_format()
            self.redirect("/paintings"+fmt,status=303)
        elif format == ".json":
            self.write(dict(paintings=paintings))
        elif format in mappings:
            content_type=mappings[format]
            self.set_header("Content-Type", content_type)
            self.render("paintings"+format, paintings=paintings)
        else:
            self.write_error(401, message="Format %s not supported" % format)
    
#Gets info on specific painting
class PaintingHandler(BaseHandler):
    def get(self, paintingID, format):
        painting= self.db.get_painting(paintingID)
        mappings= {".html":"text/html",".xml":"application/xml",".ttl":"text/turtle"}
        if format is None:
            fmt= self.get_format()
            self.redirect("/paintings/%s" %paintingID +fmt, status=303)
        elif format == ".json":
            d1 = {'success': True}
            paintingDict= dict(d1, **painting)
            #exampleDict = {'success': True, 'image': 'http://images.wikia.com/central/images/e/eb/250px-Mona_Lisa,_by_Leonardo_da_Vinci,_from_C2RMF_retouched.jpg'}
            self.write(paintingDict)
        elif format in mappings:
            content_type=mappings[format]
            self.set_header("Content-Type",content_type)
            self.render("painting"+format,painting=painting)
        else:
            self.write_error(401, message="Format %s not supported" % format)

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
        

class PaintingDatabase(object):
    """in memory database of MongoLab paintings database"""
    def __init__(self):
        #pull in full paintings collection from MongoLab
        self.apikey= "?apiKey=50c72d32e4b067a576ea9bbf"
        self.fixedURL= "https://api.mongolab.com/api/1/databases/art_history/collections/paintings"
        url = self.fixedURL + self.apikey
        f= urllib.urlopen(url)
        paintings = f.read()
        f.close()
        results= json.loads(paintings)
        self.paintings={}
        for painting in results:
            self.paintings[painting["_id"]]=painting
        
    # CRUD operations
    
    def list_paintings(self,base_uri):
        """Returns a list of all paintings"""
        paintings=[]
        for value in self.paintings.values():
            painting= dict(value)
            id= painting["_id"]
            uri= base_uri +"/paintings/"+str(id)
            del painting["_id"]
            painting["uri"]=uri 
            paintings.append(painting)
        return paintings
    
    
    def get_painting(self, paintingID):
        """Returns data about a painting"""
        painting= self.paintings[int(paintingID)]
        return painting
                    
### Script entry point ###

def main():
    tornado.options.parse_command_line()
    # Set up the database
    db = PaintingDatabase()
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