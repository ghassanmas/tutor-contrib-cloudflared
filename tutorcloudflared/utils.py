"Utils methods"

import requests
import click
from tld import get_tld, Result
from typing import Union, Optional,List,Dict

from .constants import GOOGLE_DNS_API_URL

def _get_tld_object(domain: str) -> Optional[Union[str, Result, None]]:
    return get_tld(domain, as_object=True, fix_protocol=True, fail_silently=True)

def get_first_level_domain(domain: str) -> Union[str, Result, None]:
    """
    Takes a domain as an arugment, and return the first level domain.
    1. one.two.example.com => example.com
    2. openedx.herokuapp.com => openedx.herokuapp.com
    (This because herokuapp.com is a public tld suffix)
    """
    tld_object = _get_tld_object(domain)
    if isinstance(tld_object, Result):
        return f"{tld_object.domain}.{tld_object.tld}"
    return None

def get_hosts() -> str:
    """
    This function takes the config and return a list of all
    """
    # return config['LMS_HOST']
    return ''


# def check_ns(domain:str ) -> int:
#     try:
#         result = execute("bash", "-c", f"dig {domain} +trace @1.1.1.1 | grep .cloudflare.com")
#     except:
#         result = 1
#     return result

def check_ns(domain: str) -> bool:
    """ This funciton takes a domain as argument, and check
    wether it's Name Server is cloudflare or not, by doing DOH
    (DNS over HTTPS) Using Google public free https://google.dns

    """
    request = requests.get(f"{GOOGLE_DNS_API_URL}&name={get_first_level_domain(domain)}")
    result = request.json()
    if result['Status'] == 0:
        answers = result.get('Answer',[])
        if len(answers) >0:
            ns_answers = [a.get('data','') for a in answers if a.get('date','').endswith('ns.cloudflare') ]
            return len(answers) == len(ns_answers)
    return False

    

def is_one_or_less_subdomain(domain: str) -> Union[int, None]:
    """
    This functions takes a domain as an arguments, and check weather it's 
    subdomain of a subdomain, given Cloudflare free only allows for one 
    level of subdomain.
    """
    domain_obj = _get_tld_object(domain)
    if isinstance(domain_obj, Result):
        return domain_obj.subdomain.count('.') == 0
    return None

def  strip_out_subdomains_if_needed(domain: str) -> Union[str, Result, None]:
    """
    This function takes a full domain as an argugemnt and convert
    it to one level subdomain.
    It alawys uses the last subdomain and strips out
    the subdomina(s) in between. if there are only one level
    subdomain or there isn't then it returns as it is.
    Examples:
    example.com => example.com
    one.example.com => one.example.com
    two.one.example.com => two.example.com
    two.one.example.co.uk => two.example.co.uk
    """
    tld_obj = _get_tld_object(domain)
    if isinstance(tld_obj, Result):
        return f"{tld_obj.subdomain.split('.')[0]}.{tld_obj.domain}.{tld_obj.tld}"
    return None

def is_default_domain(domain: str) -> bool:
    return f"{get_first_level_domain(domain)}" == 'overhang.io'

def is_same_domain(hosts: List[str]) -> bool:
    """
    Check if all defined public hosts are sharing same root domain
    This is done, by convertings list of hosts/domains to their  
    corresponding first level domain, add them to a set, and if they 
    are share same first level 
    """
    domains = {f"{get_first_level_domain(host)}" for host in hosts}
    return len(domains) == 1
def get_conflicted_hosts(hosts: Dict[str,str],root_domain: str)-> Dict[str,str]:
    "It filters hosts that don't share same fld with root domain"
    return {host_key:host_value for host_key, host_value in hosts.items() 
    if get_first_level_domain(host_value) != root_domain}
