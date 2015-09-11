from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
import property_utils as putil
import json
import time
import random
from api_handler.api_handler.exceptions import *

"""
	Get List of all property types and subtypes.
	return the response in format specified in api 
"""
def get_property_types(data):
	if data:
		
		data = json.loads(data)
		types_list = []
		
		for property_type in get_types():
			subtypes = get_subtypes(property_type[0])
			subtypes_list = [d.property_subtype for d in subtypes]
			types_list.append({"property_type":property_type[0],"sub_types":subtypes_list})
		
		response_msg = "Property Types Not Found" if len(types_list) == 0 else "Property Types Found"
			
		return {"operation":"Search","message":response_msg,"data":types_list}	


"""
	Get List of all Amenities.
	return the response in format specified in api 
"""
def get_amenities(data):
	if data:
		data = json.loads(data)
		amenities_list = []
		
		for property_type in get_types():
			amenities = get_amenities_subs(property_type[0])
			amenities_list.append({property_type[0]:amenities})
		
		response_msg = "Amenities Not Found" if len(amenities_list) == 0 else "Amenities Found"
			
		return {"operation":"Search","message":response_msg,"data":amenities_list}


"""
	Get List of all Flat Facilities.
	return the response in format specified in api 
"""
def get_flat_facilities(data):
	if data:
		data = json.loads(data)
		facilities_list = []
		
		for property_type in get_types():
			facilities = get_facility_subs(property_type[0])
			facilities_list.append({property_type[0]:facilities})
		
		response_msg = "Flat Facilities Not Found" if len(facilities_list) == 0 else "Flat Facilities Found"
			
		return {"operation":"Search","message":response_msg,"data":facilities_list}


def get_types():
	return frappe.db.sql("""select property_type from 
		`tabProperty Type`""",as_list=1)

def get_subtypes(property_type):
	return frappe.db.get_all("Property Subtype",
		filters={"property_type": property_type},fields=["property_subtype"])

def get_amenities_subs(property_type):
	return frappe.db.get_all("Amenities",
		filters={"property_type": property_type},fields=["amenity_name","icon"])

def get_facility_subs(property_type):
	return frappe.db.get_all("Flat Facilities",
		filters={"property_type": property_type},fields=["facility"])



""" 
	Create Group in Hunterscamp according to given request_data

"""


def create_group_in_hunterscamp(request_data):
	if request_data:
		request_data = json.loads(request_data)
		putil.validate_for_user_id_exists(request_data.get("user_id"))
		try:
			gr_doc = frappe.new_doc("Group")
			gr_doc.group_title = request_data.get("group_title")
			gr_doc.operation = request_data.get("operation")
			gr_doc.property_type =  request_data.get("property_type")
			gr_doc.property_sub_type = request_data.get("property_subtype")
			gr_doc.location = request_data.get("location")
			gr_doc.property_type_option = request_data.get("property_subtype_option")
			gr_doc.creation_via  = "Website"
			gr_doc.min_area = request_data.get("min_area",0)
			gr_doc.max_area = request_data.get("max_area")
			gr_doc.min_budget = request_data.get("min_budget",0)
			gr_doc.max_budget = request_data.get("max_budget")
			gr_doc.unit_of_area = request_data.get("unit_of_area")
			gr_doc.save()
			return {"operation":"Create", "group_id":gr_doc.name, "message":"Group Created"}
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			return {"operation":"Create", "message":"Group not created"}



def join_user_with_group_id(request_data):			
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data,["user_id","group_id"])
		if not frappe.db.get_value("Group",{"name":request_data.get("group_id")},"name"):
			raise DoesNotExistError("Group ID {0} does not exists".format(request_data.get("group_id")))
		if frappe.db.get_value("Group User",{"group_id":request_data.get("group_id"), "user_id":request_data.get("user_id")},"name"):
			raise DuplicateEntryError("Group {0} already joined".format(request_data.get("group_id")))	
		try:
			grusr = frappe.new_doc("Group User")	
			grusr.user_id = request_data.get("user_id")
			grusr.group_id = request_data.get("group_id")
			grusr.user  = email
			grusr.save()
			return {"operation":"Search", "message":"Group joined"}
		except Exception,e:
			return {"operation":"Search", "message":"Group joining operation Failed"}



def shortlist_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		if not request_data.get("property_id"):
			raise MandatoryError("Mandatory Field Property Id missing")
		if frappe.db.get_value("Shortlisted Property", {"property_id":request_data.get("property_id"), "user_id":request_data.get("user_id")} ,"name"):	
			raise DuplicateEntryError("Property {0} already Shortlisted".format(request_data.get("property_id")))
		try:
			sp_doc = frappe.new_doc("Shortlisted Property")
			sp_doc.user_id = request_data.get("user_id")
			sp_doc.property_id = request_data.get("property_id")
			sp_doc.save()
			return {"operation":"Create", "message":"Property Shortlisted" ,"property_id":request_data.get("property_id"), "user_id":request_data.get("user_id")}
		except Exception,e:
			raise OperationFailed("Shortlist Property Operation Failed")



def create_feedback(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["request_type", "feedback"])
		try:
			fdbk = frappe.new_doc("Feedback")
			fdbk.property_id = request_data.get("property_id")
			fdbk.request_type = request_data.get("request_type")
			fdbk.user_feedback = request_data.get("feedback")
			fdbk.user_ratings = request_data.get("ratings") 
			fdbk.user_id = request_data.get("user_id")
			fdbk.save()
			return {"operation":"Create", "message":"Feedback Submitted"}
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			raise e



def create_alerts(request_data):
	request_data = json.loads(request_data)
	putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		alrt = frappe.new_doc("Alerts")
		alrt.alert_title = request_data.get("alert_title")
		alrt.operation = request_data.get("operation")
		alrt.property_type =  request_data.get("property_type")
		alrt.property_subtype = request_data.get("property_sub_type")
		alrt.location = request_data.get("location")
		alrt.property_subtype_option = request_data.get("property_subtype_option")
		alrt.creation_via  = "Website"
		alrt.min_area = request_data.get("min_area",0)
		alrt.max_area = request_data.get("max_area",0)
		alrt.min_budget = request_data.get("min_budget",0)
		alrt.max_budget = request_data.get("max_budget",0)
		alrt.unit_of_area = request_data.get("unit_of_area")
		alrt.user_id = request_data.get("user_id")
		alrt.save()
		return {"operation":"Create", "alert_id":alrt.name, "message":"Alert Created"}
	except frappe.MandatoryError,e:
		raise MandatoryError("Mandatory Field {0} missing".format(e.message))
	except (frappe.LinkValidationError, frappe.ValidationError)  as e:
		raise InvalidDataError(e.message)
	except Exception,e:
		return {"operation":"Create", "message":"Alert not created"}

