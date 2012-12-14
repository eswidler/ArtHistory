#!/usr/bin/env python
# encoding: utf-8
"""
PaintingCrawler

"""
import time
import re

from SPARQLWrapper import SPARQLWrapper, JSON
from django.utils import simplejson
from httplib2 import Http

def getWikipediaPagecounts(filename):
	englishPages = dict()
	
	f = open(filename, 'r')
	
	print "Processing pagecounts file..."
	
	for line in f:
		if line.startswith("en "):
			parts = line.split(" ")
			englishPages[parts[1]] = parts[2]
	sortedEnglishPages = sorted(englishPages, key=englishPages.get, reverse=True)
	
	f.close()
	print "Pagecounts file sorted."
	return sortedEnglishPages

def getDBPediaPaintings():
	print "Retrieving DBPedia paintings..."
	
	sparql = SPARQLWrapper("http://dbpedia.org/sparql")
	sparql.setReturnFormat(JSON)
	
	sparql.setQuery("""SELECT ?category
	WHERE { ?category
	skos:broader <http://dbpedia.org/resource/Category:Paintings_by_movement_or_period>}""")

	results = sparql.query().convert()
	firstLevelPeriodCategories = []
	for result in results["results"]["bindings"]:
		firstLevelPeriodCategories.append(result["category"]["value"])
		
	#We're going one layer deeper in the categories to get more paintings
	secondLevelPeriodCategories = []
	for category in firstLevelPeriodCategories:
		secondLevelPeriodCategories.append(category)
		sparql.setQuery("SELECT ?category WHERE { ?category skos:broader <" + category + ">}")
		
		results = sparql.query().convert()
		for result in results["results"]["bindings"]:
			secondLevelPeriodCategories.append(result["category"]["value"])
		
	#Now, get the paintings
	paintingURLs = []
	for category in secondLevelPeriodCategories:
		sparql.setQuery("SELECT ?painting WHERE { ?painting dcterms:subject <" + category + ">}")
		
		results = sparql.query().convert()
		for result in results["results"]["bindings"]:
			paintingURLs.append(result["painting"]["value"])

	#Now, if it's really a painting, record tons of info on it
	print "Retrieving in-depth DBPedia painting info..."
	paintings = []
	count = 0;
	numOfPaintings = str(len(paintingURLs))
	for painting in paintingURLs:
		if (count%20 == 0):
			print "... on painting " + str(count) + " of " + numOfPaintings + "..."
		count += 1
	
		sparql.setQuery("""
		SELECT ?description, ?thumbnail, ?artist, ?city, ?title, ?type, ?year, ?bigpic
		WHERE { <""" + painting + """> dbpedia-owl:abstract ?description .
			<""" + painting + """> dbpprop:city ?city .
			<""" + painting + """> dbpprop:type ?type .
			<""" + painting + """> dbpprop:year ?year .
			<""" + painting + """> dbpprop:title ?title .
			OPTIONAL {<""" + painting + """> dbpedia-owl:thumbnail  ?thumbnail .}
			OPTIONAL {<""" + painting + """> dbpprop:artist ?artist .}
			OPTIONAL {<""" + painting + """> foaf:depiction  ?bigpic }
			FILTER (lang(?description) = "en")
			FILTER (lang(?title) = "en")
		}""") 
		
		results = sparql.query().convert()
		paintingEntry = {}
		for result in results["results"]["bindings"]:
			valid = True
			
			if "title" in result:
				paintingEntry["title"] = result["title"]["value"]
				paintingEntry["searchableTitle"] = result["title"]["value"].replace(" ", "_")
			else:
				valid = False
				
			imagePresent = False
			if "thumbnail" in result:
				paintingEntry["image"] = result["thumbnail"]["value"]
				imagePresent = True
			if "bigpic" in result:
				paintingEntry["image"] = result["bigpic"]["value"]
				imagePresent = True
			if not imagePresent:
				valid = False
				
			# Note: if a link can't be resolved to a medium, it's left as a link
			if "type" in result:
				type = result["type"]["value"]
				if not type.startswith("http://"):
					paintingEntry["medium"] = result["type"]["value"]
				else:
					sparql.setQuery("""SELECT ?label WHERE { <""" + type + """> rdfs:label ?label 
					FILTER (lang(?label) = "en")
					}""")
				
					mediumResults = sparql.query().convert()
					for mediumResult in mediumResults["results"]["bindings"]:					
						if "label" in mediumResult:				
							paintingEntry["medium"] = mediumResult["label"]["value"]
						else:
							paintingEntry["medium"] = type	
					
					if len(mediumResults["results"]["bindings"]) == 0:
						valid = False	
								
			else:
				valid = False

			# Note: if a link can't be resolved to a name, it's left as a link
			if "artist" in result:
				artist = result["artist"]["value"]
				if not artist.startswith("http://"):
					paintingEntry["artist"] = result["artist"]["value"]
				else:
					sparql.setQuery("""SELECT ?name, ?label WHERE { <""" + artist + """> foaf:name ?name .
					 <""" + artist + """> rdfs:label ?label
					 FILTER (lang(?label) = "en")
					}""")
					artistResults = sparql.query().convert()
					for artistResult in artistResults["results"]["bindings"]:						
						if "name" in artistResult:				
							paintingEntry["artist"] = artistResult["name"]["value"]
						elif "label" in artistResult:		
							paintingEntry["artist"] = artistResult["label"]["value"]
						else:
							paintingEntry["artist"] = artist

					if len(artistResults["results"]["bindings"]) == 0:
						paintingEntry["artist"] = artist	
			
			# We want both a city string and lat long coordinates	
			if "city" in result:
				cityName = result["city"]["value"]
				
				# Scenario 1: linked to dbpedia
				# Scenario 2: string, possibly with a country
				cityURL = ""
				if cityName.startswith("http://dbpedia.org/"):
					cityURL = cityName
				else:
					#Get rid of country, if it's here
					if "," in cityName:
						commaIndex = cityName.index(",")
						cityName = cityName[0:int(commaIndex)]
					cityName = cityName.replace(" ", "_")
					cityURL = "http://dbpedia.org/resource/" + cityName
				
				sparql.setQuery("""SELECT ?lat, ?long, ?name
	WHERE { <""" + cityURL + """> geo:lat ?lat .
	<""" + cityURL + """> geo:long ?long .
	<""" + cityURL + """> foaf:name ?name }""")
				
				cityResults = sparql.query().convert()
		
				for cityResult in cityResults["results"]["bindings"]:
					if "lat" in cityResult:
						paintingEntry["lat"] = cityResult["lat"]["value"]
					else:
						valid = False

					if "long" in cityResult:
						paintingEntry["lng"] = cityResult["long"]["value"]
					else:
						valid = False	
						
					if "name" in cityResult:
						paintingEntry["where"] = cityResult["name"]["value"]
					else:
						valid = False	
						
				if len(cityResults["results"]["bindings"]) == 0:
					valid = False	
					
			else:
				valid = False
			
				
			# We're looking for a year, but they can be in weirdly formatted strings
			simpleYear = re.compile("^(\d{1,4})$")
			nearYear = re.compile("^c\. (\d+)$")
			nearYear2 = re.compile("^circa (\d+)$")
			nearYear3 = re.compile("^ca. (\d+)$")
			rangeYear = re.compile("^c\. (\d+) \- (\d+)$")
			rangeYear2 = re.compile("^c\. (\d+)\-(\d+)$")			
			rangeYear3 = re.compile("^ca\. (\d+) \- (\d+)$")
			rangeYear4 = re.compile("^ca\. (\d+)\-(\d+)$")
			rangeYear5 = re.compile("^circa (\d+) \- (\d+)$")
			rangeYear6 = re.compile("^circa (\d+)\-(\d+)$")
			longYear = re.compile("^(\d+)$")
			yearWithText = re.compile("(\d{1,4})")
			
			if "year" in result:
				year = result["year"]["value"]
				
				sy = simpleYear.match(year)
				ny = nearYear.match(year)
				ny2 = nearYear2.match(year)
				ny3 = nearYear3.match(year)
				ry = rangeYear.match(year)
				ry2 = rangeYear2.match(year)
				ry3 = rangeYear3.match(year)
				ry4 = rangeYear4.match(year)
				ry5 = rangeYear5.match(year)
				ry6 = rangeYear6.match(year)
				ly = longYear.match(year)
				ywt = yearWithText.match(year)
		
				if not sy is None:
					paintingEntry["year_created"] = year
				elif not ny is None or not ny2 is None or not ny3 is None or not ry is None \
				        or not ry is None or not ry2 is None or not ry3 is None or not ry4 is None \
				        or not ry5 is None or not ry6 is None:
					substrings = re.findall(r'(\d{1,4})', year)
					if len(substrings) > 0:
						paintingEntry["year_created"] = substrings[0]
					else:
						valid = False
				elif not ly is None:
					shortYear = year[0:4]
					if (int(float(shortYear)) > -1) and (int(float(shortYear)) < 2012):
						paintingEntry["year_created"] = shortYear
					else:
						valid = False
				elif not ywt is None:
					substrings = re.findall(r'(\d{1,4})', year)
					if (len(substrings) > 0) and (int(float(substrings[0])) > -1) \
					                         and (int(float(substrings[0])) < 2012):
						paintingEntry["year_created"] = substrings[0]
					else:
						valid = False
				else:
					valid = False
			else:
				valid = False

			if "description" in result:
				paintingEntry["description"] = result["description"]["value"]
			
			if valid:
				paintings.append(paintingEntry)

	print "Finished collecting paintings."

	return paintings

def chooseDBPediaPantings(sortedEnglishPages, allPaintings):
	filteredPaintings = []
	for pageCountTitle in sortedEnglishPages:
		for painting in allPaintings:
			if painting["searchableTitle"] == pageCountTitle:
				filteredPaintings.append(painting)
				break
	
	return filteredPaintings

def insertPaintingsIntoDatabase(filteredPaintings):
	#clear and add paintings
	apikey= "?apiKey=50c6ab59e4b05e32287d6e3d"
	fixedURL= "https://api.mongolab.com/api/1/databases/art_history/collections/paintings"
	url = fixedURL + apikey

	h = Http()
	resp, content = h.request(url, "PUT", body=simplejson.dumps([]), headers={'content-type':'application/json'} )
	
	h = Http()
	resp, content = h.request(url, "POST", body=simplejson.dumps(filteredPaintings), headers={'content-type':'application/json'} )
	

def main ():
	time.ctime()
	print "Starting at" + time.strftime('%l:%M%p')
	
	sortedEnglishPages = getWikipediaPagecounts("pagecounts-20111201-040000")
	allPaintings = getDBPediaPaintings()
	filteredPaintings = chooseDBPediaPantings(sortedEnglishPages, allPaintings)
	insertPaintingsIntoDatabase(filteredPaintings)

	time.ctime()
	print "Finished at" + time.strftime('%l:%M%p')

if __name__ == "__main__":
    main()