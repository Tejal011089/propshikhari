from __future__ import unicode_literals
import api_handler
import propshikari.propshikari.propshikari_api as api
import propshikari.propshikari.property_masters as masters
import propshikari.propshikari.project_api as projt
import propshikari.propshikari.user_api as usr
from frappe.utils import cstr, cint
import frappe
import time
import json
import random
from frappe.utils.file_manager import  save_file



@frappe.whitelist()
def post_property(data):
	return api.post_property(data)


@frappe.whitelist(allow_guest=True)
def search_property(data):
	return api.search_property(data)



@frappe.whitelist(allow_guest=True)
def register_user(data):
	return usr.register_user(data)


@frappe.whitelist(allow_guest=True)
def forgot_password(data):
	return usr.forgot_password(data)



@frappe.whitelist()
def update_password(data):
	return usr.update_password(data)



@frappe.whitelist()
def get_user_profile(data):
	return usr.get_user_profile(data)


@frappe.whitelist()
def update_user_profile(data):
	return usr.update_user_profile(data)


@frappe.whitelist()
def logout(data):
	return api.log_out_from_propshikari(data)	


@frappe.whitelist(allow_guest=True)
def get_state_city_location_list(data):
	return api.get_states_cities_locations_from_propshikari(data)



@frappe.whitelist()
def update_user_image(data):
	return usr.store_image_to_propshikari(data)

	

@frappe.whitelist(allow_guest=True)
def get_property_types(data):
	return masters.get_property_types(data)


@frappe.whitelist(allow_guest=True)
def get_amenities(data):
	return masters.get_amenities(data)

@frappe.whitelist(allow_guest=True)
def get_flat_facilities(data):
	return masters.get_flat_facilities(data)


@frappe.whitelist()
def create_group(data):
	return masters.create_group_in_hunterscamp(data)


@frappe.whitelist()
def join_group(data):
	return masters.join_user_with_group_id(data)


@frappe.whitelist()
def search_group(data):
	return api.search_group_with_given_criteria(data)


@frappe.whitelist()
def get_individual_property(data):
	return api.get_property_of_given_id(data)


@frappe.whitelist(allow_guest=True)
def get_tagged_property(data):
	return api.get_property_of_particular_tag(data)


@frappe.whitelist()
def get_property_contact(data):
	return api.get_property_contact(data)

@frappe.whitelist()
def shortlist_property(data):
	return masters.shortlist_property(data)

@frappe.whitelist()
def get_shortlisted_property(data):
	return api.get_shortlisted_property(data)


@frappe.whitelist()
def get_user_properties(data):		
	return api.get_user_properties(data)


@frappe.whitelist()
def share_property(data):
	return api.share_property(data)


@frappe.whitelist()
def get_property_images(data):		
	return api.get_property_images(data)


@frappe.whitelist()
def update_property_status(data):
	return api.update_property_status(data)


@frappe.whitelist()
def report_feedback(data):
	return masters.create_feedback(data)


@frappe.whitelist()
def get_similar_properties(data):
	return api.get_similar_properties(data)


@frappe.whitelist()
def set_alert(data):
	return masters.create_alerts(data)


@frappe.whitelist()
def get_alerts(data):
	return api.get_alerts(data)


@frappe.whitelist()
def get_project_details(data):
	return projt.get_project_of_given_id(data)


@frappe.whitelist(allow_guest=True)
def search_project(data):
	return projt.search_project(data)

@frappe.whitelist()
def remove_shortlisted_property(data):
	return masters.remove_shortlisted_property(data)

@frappe.whitelist()
def validate_session(data):
	return usr.validate_for_session_exists(data)


@frappe.whitelist(allow_guest=True)
def reindex_data(data):
	return api.reindex_data(data)						





		