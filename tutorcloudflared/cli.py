
from __future__ import annotations

import subprocess

import click

from tutor.commands.context import Context
from tutor import fmt, config
from tutor.__about__ import __app__
from tutor.utils import execute
from .constants import CLOUDFLARE_NS_SETUP_URL
from .utils import check_ns, strip_out_subdomains_if_needed, is_default_domain, is_same_domain, is_one_or_less_subdomain, get_first_level_domain, get_conflicted_hosts


@click.command()
@click.pass_obj
def get_tunnel_uuid(context: Context) -> list[tuple[str, str]]:
    """
    This command is used to get tunnel UUID which is important to render config.yml file
    """
    configs = config.load(context.root)
    tunnel_name = configs.get("CLOUDFLARED_TUNNEL_NAME")
    fmt.echo_info(f"Retriving UUID of tunnel name {tunnel_name}")
    return [("cloudflared", f"cloudflared tunnel info -o json {tunnel_name} | jq -rc '.id'")]


@click.group()
def cloudflared() -> None:
    pass


@cloudflared.command()
def set_tunnel_uuid() -> list[tuple[str, str]]:
    """
    This command would set the UUID of the cloudfalred tunnel as a config value, given it would 
    be used for rednering. 
    """
    r = subprocess.run(
        ["bash", "-c", "tutor local do get-tunnel-uuid | tail -n 1"], capture_output=True, text=True)
    uuid = r.stdout.rstrip('\n')
    execute("tutor", "config", "save", "--set",
            f"CLOUDFLARED_TUNNEL_UUID={uuid}")


@cloudflared.command()
@click.pass_obj
def doctor(context: Context) -> None:
    """
This command would do the following checks in order: 
  1. It checks that user is not using the default tutor host overhang.io
  2. It checks that all hosts are sharing same root domain
  3. It checks that the root domain nameserver is handled by Cloudflare, this
    is essetial to utilize cloudflared tunnel service. 
  4. it checks if LMS_HOST is a subdomain because of cloudflare restricrtion
       If this is true then tutor by default would assing host as subdomain of 
       subdomain, however subdomain.subdomain.domain.tld can only be used if 
       user is utilziing advance certficate from cloudflare which is not free.
    """

    warnings = 0
    fatal_errors = 0
   # click.echo(result)
    configs = config.load(context.root)
    lms_host = get_first_level_domain(configs['LMS_HOST'])

    first_level_domain = get_first_level_domain(lms_host)
    is_lms_fld = first_level_domain == lms_host
    fmt.echo_info(fmt.title("Checking if it's the defautl overhang.io domain"))
    if lms_host == 'overhang.io':
        fatal_errors += 1
        fmt.echo_error("""❌ You are using the default host domain overhang.io, please reset via
        tutor config save --set LMS_HOST=mydomain.com
        And then rerun this test again
        """)
    else:
        fmt.echo_info("✅ You are not using the default domain")
    # We retrive all hosts as key value, if the host is defined in tutor config
    hosts_keys = configs.get('CLOUDFLARED_PUBLIC_HOSTS')
    undefined_hosts = [
        host_key for host_key in hosts_keys if configs.get(host_key) is None]
    defined_hosts = [
        host_key for host_key in hosts_keys if configs.get(host_key) is not None]
    domains = dict(
        (host_key, value) for host_key, value in
        [(host_key, configs.get(host_key)) for host_key in defined_hosts])
    
    # Check that all hosts share same domain
    fmt.echo_info(fmt.title("Checking if all hosts shares same root domain"))
    if is_same_domain(list(domains.values())):
        fmt.echo_info("✅ All hosts share same root domain")
    else:
        fatal_errors += 1
        # if failed retrive the hosts/domains that conflifct with the LMS
        different_hosts = get_conflicted_hosts(domains, first_level_domain)
        fmt.echo_error(
            f"❌ Not all hosts/domains share same root domain!, found {len(different_hosts.keys())}")
        for host_key, host_value in different_hosts.items():
            fmt.echo_error(f"""You need to change the host of {host_key} given it's current domain {host_value}
            conflicts with the LMS first level domain which is {first_level_domain}, you might consider 
            changing it via:""")
            fmt.echo(fmt.command(
                f"tutor config save --set {host_key}={host_value.split('.')[0]}.{first_level_domain}"))
    
    # Checking for NS records
    fmt.echo_info(fmt.title(
        f"Checking for NS records for first level domain {first_level_domain}..."))
    result = check_ns(first_level_domain)
    if result != 0:
        fmt.echo_error(f"""❌ NS checking failed!
        It doesn't seem that your domain name serever is handled by Cloudflare
        Please check this guide {CLOUDFLARE_NS_SETUP_URL}
        If you already just did that, it might need a couple of minutes for NS to prograte""")
        fatal_errors += 1
    else:
        fmt.echo_info("✅ Checking for NS settings Passed!.")

    
    #Printing the hosts that are not set, it can be beacuse, opreator are not necessary utilizing all optional services
    fmt.echo_info(
        f"Checks for domains hosts of {','.join(undefined_hosts)} will be skipped because are not defined")
    
    #Here we iterate for on each domain of every defined host:
    #And check if it's two level subdomain
    for domain_name, domain_value in domains.items():
        fmt.echo_info(f"Check for {domain_name} {domain_value}")
        subdomain_check = is_one_or_less_subdomain(domain_value)
        if not subdomain_check and subdomain_check is not None:
            new_value = strip_out_subdomains_if_needed(domain_value)
            fmt.echo(fmt.alert(f"""
           Checking for {domain_name} failed with value of {domain_value},
           becaues it's a two level subdomain, cloudflare doesn't issue 
           certificate for a two level subdomain unless you use advance cerificate 
           which would cost you about 10USD per month.
           Alternatively you might resovle this issue by changing {domain_name} to
           {new_value}, by running:\n""")+fmt.command(f"tutor config save --set {domain_name}={new_value}"))
            warnings += 1
        elif subdomain_check is None:
            fmt.echo_error(f"❌ the value of {domain_name} which is '{domain_value}' doesn't seem to be a correct domain!.")

    #Printing result of tests/checks:      
    if (fatal_errors + warnings) > 0:
        if fatal_errors > 0:
            fmt.echo(fmt.title(fmt.error(
                f"❌ Test finishied with {fatal_errors} fatal error(s) and {warnings} warning(s)")))
        elif warnings > 0:
            fmt.echo_alert(
                f"Test finishied with without fatal erros but with {warnings} warning(s)")
        fmt.echo(fmt.command(
            "Please check the suggesitons magenta color (like this color) above to fix erros or/and warning"))
    else:
        fmt.echo_info(
            fmt.title("✅ Tests done without any errors or warnings!"))
