import requests
import json

def generate_json_optimization_request(request):
    post_request = {}
    post_request['algorithm'] = request.algorithm
    post_request['robustness_fact'] = request.robustness_fact
    post_request['objective'] = {'target': request.target, 'type': request.opt_type}

    constraints = request.user_constraints.get_constraints()
    if constraints:
        post_costraints = [{'target': target, 'type': constr_type, 'value': value}
                           for target, (constr_type, value) in constraints.items()]
    else:
        post_costraints = []

    post_request['constraints'] = post_costraints

    post_request['price_per_hw'] = [{'hw':hw, 'price':price}
                              for hw, price in request.hws_prices.get_prices_per_hw().items()]
    
    if request.is_input_dependent():
        post_request['inputs'] = [{'name':name, 'value':value}
                                for name, value in request.inputs.get_inputs().items()]

    return json.dumps(post_request)

def submit_json_optimization_request(json_request, url='http://localhost:5000/optimize'):
    # Set the headers to specify that the request contains JSON data
    headers = {
        "Content-Type": "application/json"
    }

    # Send the POST request
    #response = requests.post(address+':'+str(port)+'/optimize', data=json_data, headers=headers)
    response = requests.post(url, data=json_request, headers=headers)

    return response
