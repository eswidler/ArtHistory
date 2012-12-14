#!/usr/bin/env python
# encoding: utf-8
"""

Eric Swidler, Stephanie Gary, Jessica Kane

Paint by LatLng
Main tornado webservice

"""
import os
import codecs
import json
import re
import urlparse
import urllib
import cgi

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

### Web Service implementation ###

class ArtHistory(tornado.web.Application):
    """Main Web Application Class"""
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
            (r"/paintings/([0-9a-zA-Z]+)(\..+)?", PaintingHandler), 
            (r"/paintings/([0-90-9a-zA-Z]+)/location(\..+)?", PaintingHandler),
            
            #Urls for Application's queries to the server
            (r"/pointUpdate(\..+)?", PointUpdateHandler),
            
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
    SUPPORTED_METHODS = ("GET","POST")
    
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
            
    def post(self,format):
        new_painting = json.loads(self.request.body)
        new_id = self.db.create_painting(new_painting[1])
        self.set_status(201)
        self.set_header("Location", self.base_uri + "/paintings/" + new_id)
    
#Gets info on specific painting
class PaintingHandler(BaseHandler):
    SUPPORTED_METHODS = ("PUT", "GET", "DELETE")
    
    def get(self, paintingID, format):
        painting= self.db.get_painting(paintingID,self.base_uri)
        
        if painting is None:
            self.write_error(404, message="Painting %s does not exist" %paintingID)
        else:
            mappings= {".html":"text/html",".xml":"application/xml",".ttl":"text/turtle"}
            painting['success']=True
            
            try:
                if urllib.urlopen(unicodedata.normalize('NFKD', painting['image'].decode('unicode-escape')).encode('ascii','ignore')).getcode() == 404:
                    painting['image'] = '../image_not_found.jpg'
            except IOError:
                pass
                   
            if format is None:
                fmt= self.get_format()
                self.redirect("/paintings/%s" %paintingID +fmt, status=303)
            elif format == ".json":
                #d1 = {'success': True}
                #paintingDict= dict(d1, **painting)
                self.write(painting)
            elif format in mappings:
                print(painting)
                content_type=mappings[format]
                self.set_header("Content-Type",content_type)
                self.render("painting"+format,painting=painting)
            else:
                self.write_error(401, message="Format %s not supported" % format)
            
    def put(self, paintingID, format):
        if paintingID in self.db.paintings:
            print "Updating painting %s" % paintingID
            new_painting = json.loads(self.request.body)
            self.db.update_painting(paintingID, new_painting[1])
        else:
            self.write_error(404,message="Painting %s does not exist" %paintingID)
            
    def delete(self, paintingID, format):
        if paintingID in self.db.paintings:
            print "Deleting painting %s" % paintingID
            self.db.delete_painting(paintingID)
        else:
            self.write_error(404, message="Painting %s does not exist" %paintingID)
    

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
            
            pieces= self.db.filter(yearRange,mediums)
            
            if len(pieces) > 0:
                responceDict["pieces"] = pieces
                responceDict["success"] = True
            
        self.write(responceDict)
        

class PaintingDatabase(object):
    """in memory database of MongoLab paintings database"""
    def __init__(self):
        #pull in full paintings collection from MongoLab
        self.apikey= "?apiKey=50c6ab59e4b05e32287d6e3d"
        self.fixedURL= "https://api.mongolab.com/api/1/databases/art_history/collections/paintings"
        url = self.fixedURL + self.apikey
        f= urllib.urlopen(url)
        paintings = f.read()
        f.close()
        results= json.loads(paintings)
        self.paintings={}
        self.mediums=[]
        for painting in results:
            painting['description']=cgi.escape(painting['description'],quote=True)
            self.paintings[painting["_id"]["$oid"]]=painting
            if "medium" in painting:
                if painting["medium"] not in self.mediums:
                    self.mediums.append(painting["medium"])
        
    # CRUD operations
    
    def list_paintings(self,base_uri):
        """Returns a list of all paintings"""
        paintings=[]
        for value in self.paintings.values():
            painting= dict(value)
            id= painting["_id"]
            uri= base_uri +"/paintings/"+str(id['$oid'])
            del painting["_id"]
            painting["uri"]=uri 
            paintings.append(painting)
        return paintings
    
    
    def get_painting(self, paintingID,base_uri):
        """Returns data about a painting"""
        if paintingID in self.paintings:
            painting= self.paintings[paintingID]
            uri= base_uri +"/paintings/"+str(paintingID)
            painting["uri"]=uri
            return painting
        else: 
            return None
    
    def update_painting(self, paintingID, painting):
        """Updates a painting with a given id"""
        self.paintings[paintingID] = painting
        
    def delete_painting(self, paintingID):
        """Deletes a painting"""
        del self.paintings[paintingID]
        
    def create_painting(self, painting):
        """Creates a new painting and returns the assigned ID"""
        max_id = sorted([int(paintingID) for paintingID in self.paintings])[-1]
        new_id = str(max_id + 1)
        self.paintings[new_id] = painting
        return new_id

        
    # extra functions
        
    def filter(self,yearRange,mediums):
        """Returns paintings that fit the given yearRange and mediums"""
        results=[]
        
        validMediums = ["Oil painting", "Tempera on panel", "Oil and paper on canvas", "Fresco", "Acrylic paint", "Oil on canvas"]
        for painting in self.paintings.values():
            valid= True
            if "year_created" in painting:
                if int(painting["year_created"])> int(yearRange[1]) or int(painting["year_created"])< int(yearRange[0]):
                    valid= False
            if "medium" in painting:
                    if mediums.__contains__('other') and not validMediums.__contains__(painting["medium"]):
                        valid=True
                    elif painting["medium"] not in mediums:
                        valid= False
                    
            if valid:
                results.append(painting)
        return results
                    
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
        print "\nStopping service gracefully..."
    finally:
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
    main()