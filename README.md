
# Tutor cloudflared plugin

![Top to bttom, left to right, Clouflare logo, Open edX logo, Cloudflare tunnel logo, Tutor logo. Background, Argo movie poster from Wikipedia.](./image_cover.png)
_Top to bttom, left to right, Clouflare logo, Open edX logo, Cloudflare tunnel logo, Tutor logo. Background, Argo movie poster from Wikipedia._

The tutor clouflared plugin, is a plugin that integrates Open edX tutor tool, with cloudflared service, so that it allows to run the platform, without the need to have **the machine/server http/https 80/443 necessary open the public internet**. This is done by utilizing cloudflare tunnel/proxy tool cloudflared[^1].

## Table of Contents

- [1.Use Cases](#1-use-cases)
  - [1.1 Reducing Open edX cost](#11-reducing-open-edx-cost)
  - [1.2 Sharing local development stack](#12-sharing-local-development-stack)
  - [1.3 Extra secuirty](#13-extra-security)
- [2. Installation and Usage](#2-installation-and-usage)
  - [2.1 Prerequisites](#21-prerequisites)
  - [2.2 Installation](#22-installation)
  - [2.3 Usage](#23-usage)
    - [2.3.1 Debugging/checking requirement](#231-debuggingchecking-requirement)
    - [2.3.2 Login and Initialization](#232-login-and-initialization)
    - [2.3.3 Set tunnel UUID](#233-set-tunnel-uuid)
    - [2.3.4 Launch it](#234-launch-it)
- [3. Configuration](#3-configuation)
- [4. Caveats](#4-caveats)
  - [4.1 subdomain level](#41-subdomain-level)
  - [4.2 hosts that are not subdomains of the LMS](#42-when-mfe_host-and-preview_host-not-a-suddomain-of-the-lms_host)
  - [4.3 The docker image](#43-the-docker-image)
- [5. License](#5-license)
- [6. Footnotes](#6-footnotes)
  
## 1. Use Cases

### 1.1 Reducing Open edX cost

This plugin project is also part of a personal initiative, of which the goal is to decrease the cost of running Open edX[^2]. By using this plugin, operators can deploy Open edX on-premises, as such no need for AWS, Azure, or GCP billing. thus reducing **the ongoing cost for only the yearly domain registry**.

### 1.2 Sharing local development stack

Also, another use case for this plugin can be for Open edX developers to quickly share with a client, project manager or any relevant stakeholder, what have they just developed.

### 1.3 Extra security

When using this plugin, there would be no need to allow incoming traffic to the machine/server, at the network level it should be possible[^3]

## 2. Installation and Usage

### 2.1 Prerequisites

1. Owning a domain, cost about ~12 USD per year.
2. Have the domain NS server be handled by Cloudflare, [set your nameserver to behandled by cloudfalre](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/) _if your domain is not already on cloudflare_.
3. Have tutor version >= 16 locally installed. [See tutor docs](https://docs.tutor.overhang.io/install.html)

## 2.2 Installation

Install the plugin:

```bash
pip install git+https://github.com/ghassanmas/tutor-contrib-cloudflared
```

Then enable the plugin by:

```bash
tutor plguins enable cloudflared
tutor config save
```

There are important tutor settings to be set so that `https` works as expected see [tutor proxy doc](https://docs.tutor.overhang.io/tutorials/proxy.html#running-open-edx-behind-a-web-proxy).
_This is beacuse cloudflared in a away or another runs as proxy server_

- First change the defualt site port to something other than 80 `tutor config save --set CADDY_HTTP_PORT=81`
- Change web proxy settings `tutor config save --set ENABLE_WEB_PROXY=false`

### 2.3 Usage

To utilzie this plugin,

#### 2.3.1 Debugging/checking requirement

This plugin has a specific command that  shall do all the necessary checks:

```bash
tutor cloudflared doctor
```

1. It checks that user is not using the default tutor host overhang.io
2. It checks that all hosts are sharing same root domain
3. It checks that the root domain nameserver is handled by Cloudflare, this is essetial to utilize cloudflared tunnel service.
4. it checks if LMS_HOST is a subdomain because of cloudflare restricrtion If this is true then tutor by default would assing several hosts as subdomain of subdomain. However subdomain.subdomain.domain.tld can only be used if user is utilziing advance certficate from cloudflare which is not free.

### 2.3.2 Login and Initialization

First build the image by `tutor iamges build cloudfalred`

`tutor local do init --limit=cloudflared`

Note: It has been taken care of the init script to be **Idempotent**.

The init command will do the following

1. If not logged in yet, It would ask you to login, by printing a spesfic URL, that you need to follow and choose the correct domain you intent to use for running Open edX.
2. It would create a tunnel if not exits
3. it would iterate over the public hosts (which are set via  `CLOUDFLARED_PUBLIC_HOSTS` below and create dns route for each one.
   - Note: that each host in `CLOUDFLARED_PUBLIC_HOSTS` should be defined in config.yml, otherwise it would skip it.

### 2.3.3 Set tunnel UUID

`tutor cloudflared set-tunnel-uuid`

This command would set the UUID of the cloudfalred tunnel as a config value, given it would be used for rednering.

### 2.3.4 Launch it

That's it, doing the above, should be enough to be able to luach and browse Open edX from anywhere via `tutor local luanch` or `tutor local start`

## 3. Configuation

Below are the list of the configuration their default, and how when to change them.

- `CLOUDFLARED_TUNNEL_NAME`
  - defaults: `openedx`
  - side effect when changed: needs to rerun 1) init, and 2) resetting tunnel uuid.
- `CLOUDFLARED_TUNNEL_UUID`
  - default: No deafult, it's set by the command `tutor cloudflared set-tunnel-uuid` described above.
- `CLOUDFLARED_PUBLIC_HOSTS`
  - defaults: list `['LMS_HOST', 'CMS_HOST', 'MFE_HOST','DISCOVERY_HOST', 'ECOMMERCE_HOST', 'PREVIEW_LMS_HOST']`
  - Add a host: `tutor config save --append CLOUDFLARED_PUBLIC_HOSTS=MY_SERVICE_HOST`,
    - Note: Assuming that the value of `MY_SERVICE_HOST` is set, via e.g `tutor config save --set MY_SERVICE_HOST=url`.
  - Remove a host: `tutor config save --remove CLOUDFLARED_PUBLIC_HOSTS=MY_SERVICE_HOST`

## 4. Caveats

### 4.1 subdomain level

cloudflare has a restriction of it's (proxy/free ssl) featuer that is you need to be on a premium plan so they can cover two level subdomain.[^4].

### 4.2 When MFE_HOST and PREVIEW_HOST not a suddomain of the LMS_HOST

When the LMS is not the first level domain, and given 4.1 above, then chances are that (MFE_HOST,PREVIEW_HOST) are no longer a subdomain of the LMS_HOST. If this is the siutation then if would be needed to reset the domain cookie settings, because both origins/domains the MFE and the Preview rely on a cookie that would be set by the LMS. For more info check tutor upstream issue[^5].

So if you are changing the deafult `MFE_HOST`, and `PREVIEW_HOST` **then it's important to change the cookie settings `SESSION_COOKIE_DOMAIN` or set `SHARED_COOKIE_DOMAIN`** to a value of common domain between them, this can be done by creating a tutor file plugins:

```bash
nano "$(tutor plugins printroot)"/myplugin.py
```

Of which it's content

```python
from tutor import hooks 

hooks.Filters.ENV_PATCHES.add_item(
  ("openedx-lms-common-settings",
  """
SHARED_COOKIE_DOMAIN = "{{ LMS_HOST|common_domain(PREVIEW_LMS_HOST) }}"
  """
  )
)
```

And then: enable it and save

```bash
tutor plugins enable myplugin
tutor config save 
```

And finally restart the lms.

### 4.3 The docker image

The docker image is build because the default cloudflared docker image doesn't work with tutor.

Spefically tutor expects the value of `ENTRYPOINT` not be set or to take it from docker arg. Which is not the case for cloudfalred default image[^6]

## 5. License

This software is licensed under the terms of the AGPLv3.

## 6. Footnotes

[^1]: Cloudfalre cloudflared tool, previously know as Argo Tunnel https://www.cloudflare.com/products/tunnel/  [git rpeo](https://github.com/cloudflare/cloudflared)
[^2]: See Open edX roadmap issue [openedx/platform-roadmap/issues/169](https://github.com/openedx/platform-roadmap/issues/169)
[^3]: Also called [Zero trust security model](https://en.wikipedia.org/wiki/Zero_trust_security_model)
[^4]: [Cloudfalre free ssl subdomain level](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/limitations/)
[^5]: Tutor upstream [issue#557](https://github.com/overhangio/tutor/issues/557)
[^6]: [Cloudfalred Dockerfile](https://github.com/cloudflare/cloudflared/blob/5aaab967a345124913f546b4412b0581ec570139/Dockerfile#L30)