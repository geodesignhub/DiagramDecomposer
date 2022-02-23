import json, GeodesignHub
import shapelyHelper
import logging, config
import math, json
from shapely.geometry import asShape
from shapely.geometry import Polygon
from shapely import speedups
from shapely.validation import explain_validity 
import shapelyHelper
import random
from rtree import Rtree
if speedups.available:
	speedups.enable()
	
class RTreeHelper():
	'''This class has helper functions for the RTree Spatial Index. (https://pypi.python.org/pypi/Rtree/) '''
	def getNearestBounds(self, rtree, inputbounds,):
		''' Given a set of input bounds, return a list of nearest bounds from the index ''' 
		l = list(rtree.nearest(inputbounds, 1))
		return l

	def uniqify(self, seq):
		''' Given a set of bounds keep only the uniques '''
		seen = set()
		seen_add = seen.add
		return [x for x in seq if not (x in seen or seen_add(x))]

	def extendBounds(self, origbounds, newboundslist):
		''' Given two bounds (in WGS 1984) lant long extend the bounds '''
		mins ={'minx':origbounds[0],'miny':origbounds[1]}
		maxs = {'maxx':origbounds[2],'maxy':origbounds[3]}
		for curbounds in newboundslist:
			mins['minx'] = float(curbounds[0]) if (mins['minx'] == 0) else min(float(curbounds[0]), mins['minx'])
			mins['miny'] = float(curbounds[1]) if (mins['miny'] == 0) else min(float(curbounds[1]), mins['miny'])
			maxs['maxx'] = float(curbounds[2]) if (maxs['maxx'] == 0) else max(float(curbounds[2]), maxs['maxx'])
			maxs['maxy'] = float(curbounds[3]) if (maxs['maxy'] == 0) else max(float(curbounds[3]), maxs['maxy'])

		return (mins['minx'], mins['miny'], maxs['maxx'], maxs['maxy'])

class GridGenerator():
	''' A class to generate a 1 hectare  grids '''
	def generateID(self):
		return '%030x' % random.randrange(16**30)

	def generateGrid(self, bounds):
		# xmin,ymin,xmax,ymax = bounds
		minx,miny,maxx,maxy = bounds
		# minx,maxx,miny,maxy = 448262.080078, 450360.750122, 6262492.020081, 6262938.950073
		dx = 0.01
		dy = 0.01

		nx = int(math.ceil(abs(maxx - minx)/dx))
		ny = int(math.ceil(abs(maxy - miny)/dy))

		allPolygons = {}
		allPolygonBounds = {}
		counter = 0
		for i in range(ny):
			for j in range(nx):
				counter+=1
				cf ={}
				vertices = []
				parts = []
				vertices.append((max(maxy-dy*i,miny),min(minx+dx*j,maxx)))
				vertices.append((max(maxy-dy*i,miny),min(minx+dx*(j+1),maxx)))
				vertices.append((max(maxy-dy*(i+1),miny),min(minx+dx*(j+1),maxx)))
				vertices.append((max(maxy-dy*(i+1),miny),min(minx+dx*j,maxx)))
				parts.append(vertices)
				polygon = Polygon(vertices)
				bounds = polygon.bounds
				allPolygons[counter] = polygon
				allPolygonBounds[counter]=bounds
				
				
		return allPolygons, allPolygonBounds
		
class DiagramDecomposer():
	def __init__(self):
		self.gridGenerator = GridGenerator()
		
	def genFeature(self, geom, allGeoms, allBounds,errorCounter):
		try:
			curShape = asShape(geom)
			curBounds = curShape.bounds
			allGeoms.append(curShape)
			allBounds.append(curBounds)
		except Exception as e:
			logging.error(explain_validity(curShape))
			errorCounter+=1
		return allGeoms, allBounds,errorCounter

	def processGeoms(self, inputGeoms):
		allGeoms =[]
		allBounds = []
		for curFeature in inputGeoms['features']:
			allGeoms, allBounds, errorCounter = self.genFeature(curFeature['geometry'],allGeoms=allGeoms,allBounds=allBounds, errorCounter=0)
		
		sw ={'lat':0,'lng':0}
		ne = {'lat':0,'lng':0}
		for mb in allBounds:
			sw['lat'] = float(mb[1]) if (sw['lat'] == 0) else min(float(mb[1]), sw['lat'])
			sw['lng'] = float(mb[0]) if (sw['lng'] == 0) else min(float(mb[0]), sw['lng'])
			ne['lat'] = float(mb[3]) if (ne['lat'] == 0) else max(float(mb[3]), ne['lat'])
			ne['lng'] = float(mb[2]) if (ne['lng'] == 0) else max(float(mb[2]), ne['lng'])

		bounds = (sw['lat'], sw['lng'],ne['lat'],ne['lng'])
		return allGeoms, bounds


if __name__ == "__main__":
	myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=config.apisettings['projectid'], token=config.apisettings['apitoken'])
	myGridGenerator = GridGenerator()
	myDiagramDecomposer = DiagramDecomposer()

	firstDiagID = 9 # diagram to be clipped to constraints.
	r = myAPIHelper.get_diagram(firstDiagID)

	try:
		assert r.status_code == 200
	except AssertionError as ae:
		print("Invalid reponse %s" % ae)
	else:
		op = json.loads(r.text)
		diaggeoms = op['geojson']
		sysid = op['sysid']
		desc = op['description']
		projectorpolicy = op['type']
		geoms, bounds = myDiagramDecomposer.processGeoms(diaggeoms)
		grid, allbounds = myGridGenerator.generateGrid(bounds)

	gridRTree = Rtree()
	for boundsid, bounds in allbounds.iteritems():
		gridRTree.insert(boundsid, bounds)

	choppedgeomsandareas = []
	choppedgeoms = []
	totalarea = 0
	for curgeom in geoms: 
		curbounds = curgeom.bounds
		igridids = list(gridRTree.intersection(curbounds))	
		
		for curintersectid in igridids:
			gridfeat = grid[curintersectid]
			ifeat = curgeom.intersection(gridfeat)
			ifeatarea = ifeat.area
			totalarea += ifeatarea
			ele = {'area':ifeatarea, 'feature':ifeat}
			choppedgeoms.append(ele)	

	sortedgeomsandareas = sorted(choppedgeoms, key=lambda k: k['area']) 
	
	tenpercent = ((totalarea*10)/100)
	thirtypercent = ((totalarea*30)/100)
	seventypercent = ((totalarea*70)/100)
	# print totalarea, tenpercent, thirtypercent, seventypercent
	a = 0
	tenpercentfeats={"type":"FeatureCollection", "features":[]}
	twentypercentfeats = {"type":"FeatureCollection", "features":[]}
	seventypercentfeats = {"type":"FeatureCollection", "features":[]}
	
	for cursortedgeom in sortedgeomsandareas:
		cf={}
		j = json.loads(shapelyHelper.export_to_JSON(cursortedgeom['feature']))
		cf['type']= 'Feature'
		cf['properties']= {}
		cf['geometry']= j
		if a < tenpercent:
			tenpercentfeats['features'].append(cf)
		elif a > tenpercent and a < thirtypercent:
			twentypercentfeats['features'].append(cf)
		else:
			seventypercentfeats['features'].append(cf)
		a += float(cursortedgeom['area'])


	print(json.dumps(tenpercentfeats))
	print(json.dumps(twentypercentfeats))
	print(json.dumps(seventypercentfeats))
	# opdata = [{'gj':tenpercentfeats ,'desc':"10% " +desc},{'gj':twentypercentfeats ,'desc':"20% " +desc},{'gj':seventypercentfeats ,'desc':"70% " +desc},]
	# alluploadmessages = []
	# for curopdata in opdata:
	# 	print curopdata['gj']
	# 	upload = myAPIHelper.post_as_diagram(geoms = json.dumps(curopdata['gj']), projectorpolicy= projectorpolicy,featuretype = 'polygon', description= curopdata['desc'], sysid = sysid)
	# 	alluploadmessages.append(json.loads(upload.text))

	# tenpercentfeats={"type":"FeatureCollection", "features":[]}
	# j = json.loads(shapelyHelper.export_to_JSON(finalPolygons))
	# cf['type']= 'Feature'
	# cf['properties']= {}
	# cf['geometry']= j
	# combinedGeoms.append(cf)