from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months, date_diff 
from frappe.auth import _update_password
import property_utils as putil
import json ,ast
import time
import random
from collections import OrderedDict
import datetime
from PIL import Image
import os
import base64
import elasticsearch
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import math
from api_handler.api_handler.exceptions import *



def post_property(data):
	if data:
		try:
			old_data = json.loads(data)
			email = putil.validate_for_user_id_exists(old_data.get("user_id"))
			subs_doc = putil.validate_for_postings_available(email)
			data = putil.validate_property_posting_data(old_data,"property_json/property_mapper.json")
			putil.validate_property_status(data.get("status"))
			custom_id = "PROP-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(10000,99999))
			data["property_id"] = custom_id
			meta_dict = add_meta_fields_before_posting(old_data)
			data.update(meta_dict)
			# return store_property_photos_in_propshikari(old_data.get("property_photos"),custom_id)
			property_photo_url_dict = store_property_photos_in_propshikari(old_data.get("property_photos"),custom_id)
			data["full_size_images"] = property_photo_url_dict.get("full_size",[])
			data["thumbnails"] = property_photo_url_dict.get("thumbnails",[])
			data["property_photo"] = property_photo_url_dict.get("thumbnails")[0] if len(property_photo_url_dict.get("thumbnails")) else ""
			data["posted_by"] = old_data.get("user_id")
			data["user_email"] = email
			data["posting_date"] = data.get("posting_date") if data.get("posting_date") else data["creation_date"]
			data["amenities"] = putil.prepare_amenities_data(data.get("amenities",""), data.get("property_type"))
			data["flat_facilities"] = putil.prepare_flat_facilities_data(data.get("flat_facilities",""), data.get("property_type"))
			data["possession_status"] = "Immediate" if data.get("possession") else data.get("possession_date")
			data.pop("possession_date", None)
			es = ElasticSearchController()
			response_data = es.index_document("property",data, custom_id)
			if subs_doc and response_data.get("created"):
				subs_doc.posted = cint(subs_doc.posted) + 1
				subs_doc.save(ignore_permissions=True)
			subscription = putil.get_subscriptions(email)
			response_msg = "Property posted successfully" if response_data.get("created",False) else "Property posting failed" 
			return {"operation":"Create", "message":response_msg, "property_id":response_data.get("_id"), "user_id":old_data.get("user_id"),"data":{"subscriptions":subscription}}	
		except elasticsearch.RequestError,e:
			raise ElasticInvalidInputFormatError(e.error)
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e	



def search_property(data):
	if data:
		old_property_data = json.loads(data)
		property_data = putil.validate_property_posting_data(old_property_data,"property_json/property_search.json")
		putil.isolate_city_from_location(property_data)
		try:	
			search_query = putil.generate_search_query(property_data)
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, old_property_data.get("page_number",1), old_property_data.get("records_per_page",40))
			request_id = store_request_in_elastic_search(property_data, search_query, "Property Search")
			if old_property_data.get("user_id") != "Guest":				
				response_data = check_for_shortlisted_property(response_data,old_property_data.get("user_id"))
			response_data = putil.get_date_diff_from_posting(response_data)
			response_msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
			from_record = (old_property_data.get("page_number",1) - 1) * cint(old_property_data.get("records_per_page",40)) + 1
			no_of_pages = math.ceil(flt(total_records)/old_property_data.get("records_per_page",40))
			return {"operation":"Search", "message":response_msg ,"total_records":total_records, "request_id":request_id, "records_per_page":old_property_data.get("records_per_page",40),"from_record":from_record ,"to_record":from_record +  len(response_data) - 1 if response_data else from_record + old_property_data.get("records_per_page",40) - 1,"data":response_data, "user_id":old_property_data.get("user_id"), "no_of_pages":no_of_pages}
		except elasticsearch.RequestError,e:
			raise ElasticInvalidInputFormatError(e.error)
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e


@frappe.whitelist(allow_guest=True)
def check_connection():
	return dir()





def log_out_from_propshikari(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		frappe.local.login_manager.logout()
		frappe.db.commit()
		return {"operation":"Log Out", "message":"Successfully Logged Out"}
	except Exception:
		raise LogOutOperationFailed("Log Out Unsuccessful")



def get_states_cities_locations_from_propshikari(data):
	request_data = json.loads(data)
	try:
		state_list = frappe.db.sql("select name as state_name from `tabState` ",as_dict=True)
		city_list =  frappe.db.sql("select city_name,name as city_nm,state_name from `tabCity` ",as_dict=True)
		address_list = []
		for state in state_list:
			address_dict = OrderedDict()
			address_dict["state_name"] = state.get("state_name")
			address_dict["cities"] = [  { "city_name":city.get("city_name"), "location":frappe.db.sql(" select area as location_name , lattitude as geo_location_lat ,longitude as geo_location_lon from `tabArea` where city_name='{0}'  and state_name='{1}'".format(city.get("city_nm"), state.get("state_name")),as_dict=True) }  for city in city_list if city.get("state_name") == state.get("state_name")] 
			address_list.append(address_dict)
		state_dict = {"states":address_list}	
		return { "operation":"search", "message":"States Information Found", "user_id":request_data.get("user_id"), "data":state_dict}
	except Exception,e:
		raise GetStateInfoOperationFailed("Get State info Operation Failed")





def store_request_in_elastic_search(property_data, search_query, request_type):
	request_id =  "REQ-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(100000,999999))
	request_dict = {
		"user_id":property_data.get("user_id"),
		"request_id":request_id, 
		"operation":property_data.get("operation"), 
		"property_type":property_data.get("property_type"), 
		"property_subtype":property_data.get("property_subtype"),
		"project_type":property_data.get("project_type"), 
		"project_subtype":property_data.get("project_subtype"),  
		"location":property_data.get("location"), 
		"property_subtype_option":property_data.get("property_subtype_option"), 
		"min_area":property_data.get("min_area"),
		"max_area":property_data.get("max_area"), 
		"min_budget":property_data.get("min_budget"), 
		"max_budget":property_data.get("max_budget"),
		"city":property_data.get("city"),
		"search_query":cstr(search_query),
		"request_type":request_type

	}
	meta_dict = add_meta_fields_before_posting(property_data)
	request_dict.update(meta_dict)
	es = ElasticSearchController()
	es_result = es.index_document("request",request_dict, request_id)
	return request_id


def add_meta_fields_before_posting(property_data):
	new_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	new_date = datetime.datetime.now().strftime("%d-%m-%Y")
	return {
		"created_by":property_data.get("user_id"),
		"modified_by":property_data.get("user_id"),
		"creation_date":new_date,
		"modified_date":new_date,
		"modified_datetime":new_datetime,
		"posted_datetime":new_datetime
	}



def store_property_photos_in_propshikari(request_data, custom_id):
	property_url_dict = {"full_size":[], "thumbnails":[]}
	size = 400,400
	if request_data:
		putil.validate_for_property_photo_fields(request_data)
		if not os.path.exists(frappe.get_site_path("public","files",custom_id)):
			os.makedirs(frappe.get_site_path("public","files",custom_id,"regular"))
			os.mkdir(frappe.get_site_path("public","files",custom_id,"thumbnail"))
		for property_photo in request_data:
			file_ext = property_photo.get("file_ext")	
			try:
				base64_data = property_photo.get("file_data").encode("utf8")				
				base64_data = base64_data.split(',')[1]
				imgdata = base64.b64decode(base64_data)
			 	old_file_name = "PSPI-" + cstr(time.time()) + random_string(5) + "." + file_ext
				
				with open(frappe.get_site_path("public","files",custom_id,"regular",old_file_name),"wb+") as fi_nm:
					fi_nm.write(imgdata)
				file_name = "files/" + custom_id + "/regular/" + old_file_name
				regular_image_url = frappe.request.host_url + file_name
				property_url_dict.get("full_size").append(regular_image_url)
				
				thumbnail_file_name = frappe.get_site_path("public","files",custom_id,"thumbnail",old_file_name)
				im = Image.open(frappe.get_site_path("public","files",custom_id,"regular",old_file_name))
				im.thumbnail(size, Image.ANTIALIAS)
				im.save(thumbnail_file_name)
				thumbnail_file_url = "files/" + custom_id + "/thumbnail/" + old_file_name	
				property_url_dict.get("thumbnails").append(frappe.request.host_url + thumbnail_file_url)
			except Exception,e:
				raise ImageUploadError("Image Upload Error")
	return property_url_dict




def search_group_with_given_criteria(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("request",request_data.get("request_id"))
			group_search_conditions = make_conditions_for_group_search(response)
			group_result = frappe.db.sql(""" select  name as group_id, operation, property_type , property_subtype , ifnull(property_subtype_option,"") as property_subtype_option ,ifnull(location,"") as location, ifnull(city,"") as city, ifnull(min_budget,"") as min_budget, ifnull(max_budget,"") as max_budget, ifnull(min_area,"") as min_area, ifnull(max_area,"") as max_area from `tabGroup` {0} """.format(group_search_conditions),as_dict=True)
			for group in group_result:
				join_flag = frappe.db.get_value("Group User" , {"group_id":group.get("group_id"), "user_id":request_data.get("user_id")},"name")
				group["user_joined"] = 1 if join_flag else 0
			return {"operation":"Search", "request_id":request_data.get("request_id"), "data":group_result, "message":"Matching Groups Found" if len(group_result) else "Group Not Found" }
		except elasticsearch.TransportError:
			raise DoesNotExistError("Request Id does not exists")
		except Exception,e:
			return SearchGroupOperationFailed("Search Group Operation Failed")


def make_conditions_for_group_search(response):
	group_search_conditions = "where operation='{0}' and property_subtype='{1}' and property_type='{2}' and status='Active' ".format(response.get("operation"),response.get("property_subtype"),response.get("property_type"))
	non_mandatory_fields = ["property_subtype_option", "city"]
	for field in non_mandatory_fields:
		if response.get(field):
			group_search_conditions += " and {0} = '{1}' ".format(field,response.get(field))
	if response.get("location"):
		group_search_conditions += " and location like '%{0}%' ".format(response.get("location"))
	
	range_dict = {"min_area":"max_area", "min_budget":"max_budget"}
	
	for min_field,max_field in range_dict.items():
		if response.get(min_field) and not response.get(max_field):
			group_search_conditions += " and  {0} >= {1} ".format(min_field, response.get(min_field))
		elif not response.get(min_field) and response.get(max_field):
			group_search_conditions += " and {0} <= {1} ".format(max_field , response.get(max_field))
		elif response.get(min_field) and response.get(max_field):
			group_search_conditions += " and {0} >= {1} and {2} <= {3}".format(min_field, response.get(min_field),max_field , response.get(max_field)) 			
	return group_search_conditions


def get_property_of_given_id(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"), ["property_photos"])
			return {"operation":"Search", "message":"Property found" if len(response) else "Property Not Found", "user_id":request_data.get("user_id"), "data":response}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except Exception,e:
			raise GetPropertyOperationFailed("Get Property Operation Failed")



def get_property_of_particular_tag(request_data):
	if request_data:
		request_data = json.loads(request_data)
		if not request_data.get("tag"):
			raise MandatoryError("Mandatory Field Tag missing")
		try:
			search_query = { "query":{ "match":{ "tag":request_data.get("tag") } }  } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))	
			response_msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1
			return {"operation":"Search", "message":response_msg ,"total_records":total_records, "records_per_page":request_data.get("records_per_page",40),"from_record":from_record ,"to_record": from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1,"data":response_data, "user_id":request_data.get("user_id"), "tag":request_data.get("tag")}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get Tagged Property Operation Failed")



def get_property_contact(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))	
		if not request_data.get("property_id"):
			raise MandatoryError("Mandatory Field Property Id missing")
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"),[],["agent_name", "agent_no", "contact_no" ,"contact_person"])
			return {"operation":"Search", "message":"Contact Details found" if len(response) else "Contact Details Not Found", "user_id":request_data.get("user_id"), "data":response}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except Exception,e:
			raise OperationFailed("Get Property Contact Operation Failed")



def get_shortlisted_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		property_ids_list = frappe.db.get_values("Shortlisted Property", {"user_id":request_data.get("user_id")}, "property_id")
		if not property_ids_list:
			return {"operation":"Search", "message":"No Single Shortlisted property found", "user_id":request_data.get("user_id")}
		property_ids_list = [ property_id[0] for property_id in property_ids_list if property_id]
		try:
			search_query = { "query":{ "ids":{ "values":property_ids_list } }  } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))	
			for response in response_data:
				new_list = response.get("tag",[])
				new_list.append("Shortlisted")
				response["tag"] = new_list
			response_msg = "Shortlisted Property Found" if len(response_data) else "Shortlsited Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1
			return {"operation":"Search", "message":response_msg ,"total_records":total_records, "records_per_page":request_data.get("records_per_page",40),"from_record":from_record ,"to_record": from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1,"data":response_data, "user_id":request_data.get("user_id")}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
		 	raise OperationFailed("Get Shortlisted Property Operation Failed")



def get_user_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { "query": { "match":{ "posted_by":request_data.get("user_id") } } }
		try:
			es = ElasticSearchController()
			response_data, total_records  = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))
			response_data = check_for_shortlisted_property(response_data, request_data.get("user_id"))
			response_msg = "User Property Found" if len(response_data) else "User Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1 
			return {"operation":"Search", "message":response_msg ,"total_records":total_records, "records_per_page":request_data.get("records_per_page",40),"from_record":from_record ,"to_record": from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1,"data":response_data, "user_id":request_data.get("user_id")}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get User Properties Operation Failed")



def check_for_shortlisted_property(response_data, user_id):
	short_prop = frappe.db.get_values("Shortlisted Property",{"user_id":user_id}, "property_id" ,as_dict=True)
	short_prop = [sp.get("property_id") for sp in short_prop if sp]
	for response in response_data:
		if response.get("property_id") in short_prop:
			new_list = response.get("tag",[])
			new_list.append("Shortlisted")
			response["tag"] = new_list
	return response_data		



def share_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		user_name = frappe.db.get_value("User", email, ["first_name", "last_name"],as_dict=True)
		putil.validate_property_data(request_data, ["comments", "email_id"])		
		try:
			property_ids_list = {  comment.get("property_id"):comment.get("comment","")  for comment in request_data.get("comments") if comment.get("property_id")}
			search_query = { "query":{ "ids":{ "values":property_ids_list.keys() } }} 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))				
			if response_data:
				for response in response_data:
					response["comments"] = property_ids_list.get(response.get("property_id"),"")
				args = { "title":"Property Shared by  {0}".format(email) , "property_data":response_data ,"first_name":user_name.get("first_name"), "last_name":user_name.get("last_name")}
				send_email(request_data.get("email_id"), "Propshikari properties shared with you", "/templates/share_property_template.html", args)
				return { "operation":"Share", "message":"Property Shared"}
			else:
				raise DoesNotExistError("Property Id does not exists in elastic search")
		except frappe.OutgoingEmailError:
			raise OutgoingEmailError("Email can not be sent,Outgoing email error")
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Share Property Operation Failed")




def send_email(email, subject, template, args):
	frappe.sendmail(recipients=email, sender=None, subject=subject,
			message=frappe.get_template(template).render(args))



def get_property_images(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		if not request_data.get("property_id"):
			raise MandatoryError("Property Id not provided")
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"),[],["full_size_images", "thumbnails"])
			return { "operation":"Search", "message":"Property Images Found" if response else "Property Images Not Found", "user_id":request_data.get("user_id"), "data":response }
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)	
		except Exception,e:
			raise OperationFailed("Get Property Images Operation Failed")



def update_property_status(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["property_id"])
		putil.validate_property_status(request_data.get("property_status"))	
		try:
			search_query = {"doc":{ "status":request_data.get("property_status") }}
			es = ElasticSearchController()
			response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
			return {"operation":"Update" , "message":"User property status changed" if response else "Property Status not changed", "user_id":request_data.get("user_id")}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)	
		except Exception,e:
			raise OperationFailed("Update Property Status Operation Failed")



def get_similar_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["request_type", "id"])
		search_dict = {"property_id":get_search_query_of_property_id ,"request_id":get_search_query_of_request_id}
		if request_data.get("request_type") not in ["property_id", "request_id"]:
			raise InvalidDataError("Request type contains Invalid Data")
		search_query = search_dict.get(request_data.get("request_type"))(request_data)
		try:
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",3))
			from_record =  ((request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",3)) + 1 )
			response_msg = "Similar Property Found" if response_data else "Similar property not found"
			no_of_pages = math.ceil(flt(total_records)/request_data.get("records_per_page",3))
			return {"operation":"Search", "message":response_msg ,"total_records":total_records,"records_per_page":request_data.get("records_per_page",3),"from_record":from_record ,"to_record": from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",3) - 1 ,"data":response_data, "user_id":request_data.get("user_id"), "no_of_pages":no_of_pages}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get Similar property Operation Failed")	 


def get_search_query_of_property_id(request_data):
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("property",request_data.get("id"))		
		search_query = putil.generate_search_query_from_property_data(response)
		return search_query
	except elasticsearch.TransportError:
		raise DoesNotExistError("Property Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)	


def get_search_query_of_request_id(request_data):
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("request",request_data.get("id"),[],["search_query"])
		search_query = ast.literal_eval(response.get("search_query").encode("utf8"))
		return search_query
	except elasticsearch.TransportError:
		raise DoesNotExistError("Request Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)		
		

def get_alerts(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		alert = frappe.db.sql("select * from `tabAlerts` where user_id='{0}' order by creation desc limit 1".format(request_data.get("user_id")),as_dict=1)
		try:
			if alert:
				property_search_query = putil.generate_search_query(alert[0])
				new_query = property_search_query.get("query").get("bool").get("must")
				new_query.append({
								    "range" : {
								        "posted_datetime" : {
								            "gte": alert[0].get("creation").strftime("%Y-%m-%d %H:%M:%S"),
								        }
								    }
								})
				property_search_query["query"]["bool"]["must"] = new_query
			else:
				search_query = {	
									"sort": [{ "posted_datetime": { "order": "desc" }}],
									"query":{ "bool":{ "must":[ {"match":{ "user_id":request_data.get("user_id")  } } ] }    } 
								}						
				es = ElasticSearchController()
				response_data, total_records = es.search_document(["request"], search_query, 1, 1)
				if response_data:
					last_month_date = add_months(datetime.datetime.now() ,-1).strftime("%Y-%m-%d %H:%M:%S")
					property_search_query = response_data[0].get("search_query")
					property_search_query = ast.literal_eval(property_search_query.encode("utf8"))
					new_query = property_search_query.get("query").get("bool").get("must")
					new_query.append({
										    "range" : {
										        "posted_datetime" : {
										            "gte":last_month_date,
										        }
										    }
										})
					property_search_query["query"]["bool"]["must"] = new_query
				else:
					raise OperationFailed("No Alerts and Request Id found against User {0}".format(email))
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], property_search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))
			from_record =  ((request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1 )
			response_msg = "Property Found" if response_data else "Property not found"
			no_of_pages = math.ceil(flt(total_records)/request_data.get("records_per_page",40))
			return {"operation":"Search", "message":response_msg ,"total_records":total_records,"records_per_page":request_data.get("records_per_page",40),"from_record":from_record ,"to_record": from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1 ,"data":response_data, "user_id":request_data.get("user_id"), "no_of_pages":no_of_pages}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e




def reindex_data(data):
	try:
		request_data = json.loads(data)
		es = Elasticsearch()
		helpers.reindex(client=es, source_index=request_data.get("source"), target_index=request_data.get("target"))
		return {"data":"sucess"}
	except elasticsearch.ElasticsearchException,e:
		return {"new":dir(e),"mes":e.message, "error":e.errors}									







