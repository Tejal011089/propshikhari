from __future__ import unicode_literals
import frappe
import os
import time
import json
from api_handler.api_handler.exceptions import *
from frappe.utils import cstr, cint, date_diff
from dateutil import relativedelta
from datetime import datetime



def validate_property_data(data, property_field_list):
	
	"""  
	    Validate if given mandatory property from property_field_list exists in request data.
	    If not found then user request will not procced further.

	"""
	
	for property_field in property_field_list:
		if not data.get(property_field,False):
			raise MandatoryError("Mandatory field {0} missing".format(property_field))
	return True	

def generate_search_query(property_data):

	""" 
        Generate search query for property search from given sets of criteria 
        like property-type, property_subtype, budget, area etc.

	"""
	

	property_field_dict = {"operation":"operation", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option", "city":"city"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	
	range_field_dict = { "carpet_area":["min_area", "max_area"], "price" :["min_budget", "max_budget"] }
	range_dict = {}
	for key,value in range_field_dict.items():
		result = get_range_query(key,value,property_data)
		if result:
			range_dict[key] = result		
	if range_dict:
		range_list = [ {"range": {range_key:range_value} } for range_key,range_value in range_dict.items() ]
		must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	return search_query	

def get_range_query(key,value,request_data):
	new_dict = {}
	if request_data.get(value[0]) and request_data.get(value[1]):
		new_dict["gte"] = request_data.get(value[0])
		new_dict["lte"] = request_data.get(value[1])
	elif request_data.get(value[0]) and not request_data.get(value[1]):
		new_dict["gte"] = request_data.get(value[0])
	elif not request_data.get(value[0]) and request_data.get(value[1]):
		new_dict["gte"] = 0
		new_dict["lte"] = request_data.get(value[1])
	return new_dict			


def validate_property_posting_data(property_data,file_name):

	" Validate property posting data for valid datatype, fields and for mandatory fields "


	property_mapper = {}
	with open(os.path.join(os.path.dirname(__file__),file_name),"r") as pi:
		property_mapper = json.loads(pi.read())

	property_mapper_keys = property_mapper.keys()
		
	for field_name,schema in property_mapper.items():
		if schema.get("is_mandatory") and not property_data.get(field_name,False):
			raise MandatoryError("Mandatory field {0} missing".format(field_name))
		elif property_data.has_key(field_name):
			validate_for_field_type(schema, property_data.get(field_name), field_name)
	
	return {key:property_data.get(key) for key in property_data if key in property_mapper_keys}



def validate_for_field_type(schema, field_value, field_name):
	field_type = schema.get("field_type")
	type_mapper = {"string":unicode, "number":(int,long,float), "integer":int, "list":list, "object":dict, "nested":list}
	if not isinstance(field_value,type_mapper.get(field_type)):
		raise InvalidDataError("Invalid input of field {0}".format(field_name))
	if field_type == "nested":
	   if isinstance(field_value,list):
			for key in field_value:
				if not isinstance(key,dict):
					raise InvalidDataError("Invalid input of field {0}".format(field_name))



def validate_for_user_id_exists(user_id):
	email = frappe.db.get_value("User", {"user_id": user_id}, "email")
	if not email:
		raise DoesNotExistError("User id does not exists")					 
	return email


def generate_hash(txt=None):
	import hashlib
	return hashlib.sha224((txt or "") + repr(time.time()))


def validate_for_property_photo_fields(request_data):
	for property_photo in request_data:
		if not property_photo.get("file_data"):
			raise MandatoryError("File data not found in property photo")
		if not property_photo.get("file_ext"):
			raise MandatoryError("File extension not found in property photo")


def validate_property_status(status):
	if not status:
		raise MandatoryError("Property Status Not found")	
	else:
		if status not in ["Deactivated" ,"Active", "Sold"]:
			raise InvalidDataError("Invalid input of property status field")




def generate_search_query_from_property_data(property_data):

	""" 
        Generate search query for get similar property from given sets of criteria 
        like property-type, property_subtype, budget, area etc.

	"""

	
	property_field_dict = {"operation":"operation", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option", "city":"city"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	range_list = range_list = [ {"range": {range_key:{"lte":property_data.get(range_key)}} } for range_key in ["carpet_area","price"] if property_data.get(range_key,False)]
	must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	return search_query				


def validate_for_postings_available(email):
	subs_name = frappe.db.get_value("User Subscription",{"user":email},"name")
	if subs_name:
		subs_doc = frappe.get_doc("User Subscription",subs_name)
		remaining = cint(subs_doc.allowed) - cint(subs_doc.posted)
		if remaining == 0:
			raise ValidationError("Posting Limit Exhausted")
		else:
			return subs_doc					 

def get_subscriptions(user):
	subs_dic = {}
	subs_name = frappe.db.get_value("User Subscription",{"user":user},"name")
	if subs_name:
		subs_doc = frappe.get_doc("User Subscription",subs_name)
		subs_dic["posting_allowed"] = cint(subs_doc.allowed)
		subs_dic["total_posted"] = cint(subs_doc.posted) or 0
		subs_dic["posting_available"] = cint(subs_doc.allowed) - cint(subs_doc.posted)
	return subs_dic



def prepare_amenities_data(amenities_data, property_type):
	amenities = []
	amenity_list = frappe.db.sql(" select ifnull(amenity_name,'') as name ,ifnull(icon,'') as image  from `tabAmenities` where property_type='{0}' ".format(property_type),as_dict=True)
	for amenity in amenity_list:
		amenity_dict = {}
		amenity_dict["status"] = "Yes" if amenity.get("name") in amenities_data else "No"
		amenity_dict["name"] = amenity.get("name")
		amenity_dict["image"] = amenity.get("image")
		amenities.append(amenity_dict)
	return amenities


def prepare_flat_facilities_data(facility_data, property_type):
	flat_facilities = []
	flat_facilities_list = frappe.db.sql(" select ifnull(facility,'') as name ,ifnull(icon,'') as image  from `tabFlat Facilities` where property_type='{0}' ".format(property_type),as_dict=True)
	for flat_facility in flat_facilities_list:
		facility_dict = {}
		facility_dict["status"] = "Yes" if flat_facility.get("name") in facility_data else "No"
		facility_dict["name"] = flat_facility.get("name")
		facility_dict["image"] = flat_facility.get("image")
		flat_facilities.append(facility_dict)
	return flat_facilities


def get_date_diff_from_posting(response_data):
	for response in response_data:
		current_date = datetime.now()
		if response.get("posting_date"):
			posting_date = datetime.strptime(response.get("posting_date"), "%d-%m-%Y")
			r = relativedelta.relativedelta(current_date, posting_date) 
			if r.years:
				response["elapsed_time"] = "{0} year ago".format(r.years)
			elif r.months:
				response["elapsed_time"] = "{0} month ago".format(r.months)
			elif r.days:
				response["elapsed_time"] = "{0} days ago".format(r.days)
	return response_data


def isolate_city_from_location(property_data):
	if property_data.get("location"):
		location_city_list = property_data.get("location").split(',')
		if len(location_city_list) == 2: 
			property_data["location"] = location_city_list[0]
			property_data["city"] = location_city_list[1]
		elif len(location_city_list) > 2:
			raise InvalidDataError("Invalid Input of Location Field")


def generate_project_search_query(project_data):

	""" 
        Generate search query for project search from given sets of criteria 
        like project-type, project_subtype, budget, area etc.

	"""
	

	project_field_dict = {"operation", "project_type", "project_subtype", "location", "city"}
	must_clause_list = [ {"match":{ project_field : project_data.get(project_field) } } for project_field in project_field_dict if project_data.get(project_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	range_dict = {	
					"property_details.min_area":["min_area","gte"], 
					"property_details.max_area":["max_area", "lte"], 
					"property_details.min_price":["min_budget","gte"], 
					"property_details.max_price":["max_budget","lte"]
				}	
	range_list = [ {"range": {range_key: {range_value[1]:project_data.get(range_value[0])  } } } for range_key,range_value in range_dict.items() if project_data.get(range_value[0])]
	filter_query = prepare_nested_query(range_list) if range_list else {}
	search_query = { "query": { "filtered":{ "query":{ "bool":{ "must":must_clause_list } }, "filter":filter_query}   }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	return search_query


def prepare_nested_query(range_list):
	return { "nested":
				{ 
					"path":"property_details",
					"query":{ 
						"bool":{ "must":range_list }  
					} 
				} 
			}




