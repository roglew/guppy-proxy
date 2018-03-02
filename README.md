# Guppy Proxy

The Guppy Proxy is an intercepting proxy for performing web application security testing. Its features are often similar to, or straight up rippoffs from [Burp Suite](https://portswigger.net/burp/). However, Burp Suite is expensive which makes a proxy like Guppy inevitable.

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_main.png)

# Installation

## Dependencies

Make sure the following commands are available:

* `python3`
* `pip`
* `virtualenv` (can be installed with pip)
* `go` version 1.8 or higher

## Installing

1. Clone this repo somewhere it won't get deleted: `git clone https://github.com/roglew/guppy-proxy.git`
1. `cd /path/to/guppy-proxy`
1. `./install.sh`
1. Test that it starts up and generate certs: `./start` (keep it open and continue to test it works)
1. Copy/symlink the `start` script somewhere in your PATH (i.e. `~/bin` if you have that included) and rename it to `guppy` if you want
1. Add the CA cert in `~/.guppy/certs` to your browser as a CA
1. Configure your browser to use `localhost:8080` as a proxy
1. Navigate to a site and look at the history in the main window

## Updating

1. Navigate to the guppy-proxy folder with this repo in it
1. `git pull` to pull the latest version
1. run `./install.sh` again

The same start script as before should still work

## Uninstalling

1. Delete the guppy-proxy directory you made during installation
1. Delete `~/.guppy`
1. Remove the start script from wherever you put it

# How to Use Guppy

## History View

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_main.png)
![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_view_pretty.png)
![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_tree.png)

The first thing you see when you open Guppy is the history view. As requests pass through the proxy they are displayed in the lower half of the window. You can click a request to view the full request/response in the windows on the upper half or right click them for more options. The tabs on the upper half will let you view additional information about the selected request:

* Messages - The full request/response
* Info - A list of values associated with the message
* Tags - Lets you view/edit the tags currently associated with the request

The bottom half has tabs which relate to all of the requests that have been recorded by the proxy:

* List - A list of all of the requests that have been recorded by the proxy
* Tree - A site map of all of the endpoints visited
* Filters - An advanced search interface which is described below in the Filters section

## Filters and Search

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_search.png)

Guppy's main selling point over other similar proxies is its search. You can search for a wide variety of fields within a request or response and apply more than one search condition at the same time. This allows you to perform complex searches over your history so that you can always find the request that you want. You would be surprised what you can find when searching for paths, headers, and body contents. For example you can find potential CSRF targets by finding requests which are not GET requests and also do not have a header with "CSRF" in it.

How to apply a filter to your search:

1. Select the field you want to search by
1. Select how you want to search it (whether it contains a value, matches a regexp, is an exact value, etc)
1. Enter the value to search by in the text box
1. Click "Ok" or press enter in the text box

Once you apply a filter, the "list" and "tree" tabs will only include requests which match ALL of the active filters.

In addition, you can apply different filters for the key and value of key/value fields (such as headers or request parameters). This can be done by:

1. Select a key/value field such as "Rsp. Header" or "URL Param"
1. Click the "+" button on the right
1. Enter the filter for the key on the left and the filter for the value on the right
1. Click "Ok" or press enter in one of the text boxes

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_search_kv.png)

And that's it! The filter tab has the following additional controls:

1. Clear - Delete all active filters
1. Pop - Delete the most recent filter
1. Scope - Set the active search to your project's scope (see below)
1. Save Scope - Set your project's scope to the currently active filters (see below)
1. Apply a built-in filter dropdown - Guppy has a list of commonly useful filters. Select one from this list to apply it

### Text Filter Entry

Along with the provided dropdowns you can manually type in a filter by clicking the `>` button. In some cases it may be faster to type your filter out rather than clicking on dropdowns. In addition it allows you to create filter statements that contain an `OR` and will pass a request that matches any one of the given filters. In fact, all the dropdown input does is generate these strings for you.

Most filter strings have the following format:

```
<field> <comparer> <value>
```

Where `<field>` is some part of the request/response, `<comparer>` is some comparison to `<value>`. For example, if you wanted a filter that only matches requests to `target.org`, you could use the following filter string:

```
host is target.org

field = "host"
comparer = "is"
value = "target.org"
```

For fields that are a list of key/value pairs (headers, get params, post params, and cookies) you can use the following format:

```
<field> <comparer1> <value1>[ <comparer2> <value2>]
```

This is a little more complicated. If you don't give comparer2/value2, the filter will pass any pair where the key or the value matches comparer1 and value1. If you do give comparer2/value2, the key must match comparer1/value1 and the value must match comparer2/value2 For example:

```
Filter A:
    cookie contains Session

Filter B:
    cookie contains Session contains 456

Filter C:
    inv cookie contains Ultra

Cookie: SuperSession=abc123
Matches A and C but not B

Cookie: UltraSession=abc123456
Matches both A and B but not C
```

#### List of fields

| Field Name | Aliases | Description | Format |
|:--------|:------------|:-----|:------|
| all | all | Anywhere in the request, response, or a websocket message | String |
| reqbody | reqbody, reqbd, qbd, qdata, qdt | The body of the request | String |
| rspbody | rspbody, rspbd, sbd, sdata, sdt | The body of the response | String |
| body | body, bd, data, dt | The body in either the request or the response | String |
| wsmessage | wsmessage, wsm | In a websocket message | String |
| method | method, verb, vb | The request method (GET, POST, etc) | String |
| host | host, domain, hs, dm | The host that the request was sent to | String |
| path | path, pt | The path of the request | String |
| url | url | The full URL of the request | String |
| statuscode | statuscode, sc | The status code of the response (200, 404, etc) | String |
| tag | tag | Any of the tags of the request | String |
| reqheader | reqheader, reqhd, qhd | A header in the request | Key/Value |
| rspheader | rspheader, rsphd, shd | A header in the response | Key/Value |
| header | header, hd | A header in the request or the response | Key/Value |
| param | param, pm | Either a URL or a POST parameter | Key/Value |
| urlparam | urlparam, uparam | A URL parameter of the request | Key/Value |
| postparam | postparam, pparam | A post parameter of the request | Key/Value |
| rspcookie | rspcookie, rspck, sck | A cookie set by the response | Key/Value |
| reqcookie | reqcookie, reqck, qck | A cookie submitted by the request | Key/Value |
| cookie | cookie, ck | A cookie sent by the request or a cookie set by the response | Key/Value |

#### List of comparers

| Field Name | Aliases | Description |
|:--------|:------------|:-----|
| is | is | Exact string match | 
| contains | contains, ct | A contain B is true if B is a substring of A |
| containsr | containsr, ctr | A containr B is true if A matches regexp B |
| leneq | leneq | A Leq B if A's length equals B (B must be a number) |
| lengt | lengt | A Lgt B if A's length is greater than B (B must be a number ) |
| lenlt | lenlt | A Llt B if A's length is less than B (B must be a number) |

#### Special form filters

A few filters don't conform to the field, comparer, value format. You can still negate these.

| Format | Aliases | Description |
|:--|:--|:--|
| invert <filter string> | invert, inv | Inverts a filter string. Anything that matches the filter string will not pass the filter. |

Examples:

```
Show state-changing requests
  inv method is GET

Show requests without a csrf parameter
  inv param ct csrf
```

#### Using OR

If you want to create a filter that will pass a request if it matches any of one of a few filters you can create `OR` statements. This is done by entering in each filter on the same line and separating them with an `OR` (It's case sensitive!).

Examples:

```
Show requests to target.org or example.com:
    host is target.org OR host is example.com

Show requests that either are to /foobar or have foobar in the response or is a 404
    path is /foobar OR sbd ct foobar OR sc is 404
```

### Scope

The scope of your project describes which requests should be recorded as they pass through the proxy. Guppy allows you to define a set of filters which describe which requests are in scope. For example, if your scope is just `host ctr example.com$` only requests to example.com will be recorded in history.

To set the scope of your project:

1. Enter the filters you want to be your scope
1. Press the "Save Scope" button

And you're done! Requests that do not match this set of filters will no longer be saved. You can also set your current search to your scope by clicking the "Scope" button. The scope can be deleted by pressing the "Clear" button to delete all active filters and then clicking "Save Scope".

# Repeater

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_repeater.png)

The repeater lets you repeatedly tweak and submit a request. You can use a request in the repeater by:

1. Find the request you which to resubmit in the history list view
1. Right click the request and click "Send to Repeater"
1. Navigate to the repeater tab
1. Edit the request on the left
1. Click the submit button

When you click submit:

* The request will be submitted
* The request and response will be saved in history
* Any tags under the "tag" tab will be applied to the request

# Interceptor

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_interceptor.png)

The interceptor lets you edit requests and responses as they pass through the proxy. To use this:

1. Navigate to the interceptor tab
1. Click the "Int. Requests" and/or the "Int. Responses" buttons
1. Wait for a request to pass through the proxy
1. Edit the message in the text box then click "Forward" to forward the edited message or click "Cancel" to just drop the message altogether

# Decoder

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_decoder.png)

The decoder allows you to perform common encoding/decoding actions. You use the decoder by:

1. Paste the data that you want to encode/decode
1. Select how you wish to encode/decode it
1. Press "Go!"

The text will be processed and it will appear in the same text box. Easy!

# Macros

Guppy includes support for loading and executing Python scripts in order to allow for more complex attacks than can be performed by hand with the repeater. It is worth noting that **this feature is not user friendly. Use it at your own risk.** No attempt is made to make this feature user-friendly, stable, or good. The main reason it exists is to make it easier to write python scripts which integrate with Guppy history and to provide some way to extend Guppy's features without a pull request. If you haven't been scared away yet, read on.

There are two types of macros that you can write:

* Active macros: Take requests as an input, make more requests, edit the input requests, etc, then output a new set of requests for review
* Intercepting macros: Modify requests and responses as they pass through the proxy

Most features that you want will fall into one of those categories. Both macros are created by creating a `.py` file and defining specific functions which will be run when the macro is executed. For example an active macro must define `run_macro` and an intercepting macro must define `mangle_request` and/or `mangle_response`. See their respective sections below for more details.

## The API

Unfortunately since this feature was pretty much just thrown together for my own use, the documentation is looking at the source. Hopefully it will become more stable once Guppy development slows down, but for now you'll have to look at the relevant classes to figure out how to do stuff on your own. The following classes are the most important when writing a macro:

### MacroClient

`MacroClient` is defined in `(guppyproxy/macro.py)` and is the interface that macros use to submit requests, save requests to history, and produce output. At the time of writing the class provides:

```
MacroClient.submit(req, save=False): Submits a request to the server and sets req.response to the response. req is the HTTPRequest to submit. req.dest_host, req.dest_port, and req.use_tls will be used to determine the location to submit the request to
MacroClient.save(req): Permenantly saves an HTTPRequest to history
MacroClient.output(s): Prints a string to the output tab in the macros interface
MacroClient.output_req(req): Adds a request to the output request table in the macros interface
MacroClient.new_request(method="GET", path="/", proto_major=1, proto_minor=1,
                        headers=None, body=bytes(), dest_host="", dest_port=80,
                        use_tls=False, tags=None): Creates a new HTTPRequest from scratch that can be submitted with the client
```

### HTTPRequest and HTTPResponse

`HTTPRequest` and `HTTPResponse` are defined in `guppyproxy/proxy.py`. These classes represent HTTP messages. `HTTPRequest` contains both the contents of the message and information about its intended destination (host, port, whether to use TLS). Below are a few examples on how to use these classes, however for more deails you will need to consult `proxy.py`:

```python
req = HTTPRequest()
rsp = HTTPResponse()

req2 = req.copy() # Copy a request
rsp2 = rsp.copy() # Copy a response

# Refer to the messages associated with a messages
rsp3 = req.response # Response to a request, will be `None` if there was no response
unm = req.unmangled # Unmangled version of a request, is `None` if none exist
unm2 = rsp.unmangled # Unmangled version of a response, is `None` if none exist

# Get the full message of an object (is a bytes())
full_req = req.full_message()
full_rsp = rsp.full_message()

# Get timing info for a request
tstart = req.time_start # datetime.datetime when the request was made
tend = req.time_end # datetime.datetime when the request's response was received

# Get destination info from a request
dest_host = req.dest_host
dest_port = req.dest_port
use_tls = req.use_tls

# Get/set the method of a request
m = req.method # Get the method of the request
req.method = "POST" # Set the method of the request

# Get/set url info of a request
requrl = req.full_url() # get the full URL of a request
path = req.url.path # get the path of a request
req.url.path = "/foo/bar/baz" # set the path of a request
v = req.url.get_param("foo") # get the value of the "foo" URL parameter
req.url.set_param("foo", "bar") # set the value of the "foo" URL parameter to "bar"
req.url.add_param("foo", "bar2") # add a URL parameter allowing duplicates
req.url.del_param("foo") # delete a url parameter
[(k, v) for k, v in req.url.param_iter] # iterate over all the key/value pairs in the URL parameters
frag = req.url.fragment # get the fragment of the url (the bit after the #)
req.url.fragment = "frag" # set the url fragment of the request

# Manage headers in a message
req.headers.set("Foo", "Bar") # set a header, repalcing existing value
hd = req.headers.get("Foo") # get the value of a header (for duplicates, returns first value)
req.headers.add("Foo", "Bar2") # add a header without replacing an existing one
pairs = req.headers.pairs() # returns all the key/value pairs of the headers in the message
req.headers.delete("Foo") # delete a header
req.headers.dict() # Returns a dict of the headers in the form of {"key1": ["val1", "val2"], "key2": ["val3", "val4"]}
# Same for responses
rsp.headers.set("Foo", "Bar")
hd = rsp.headers.get("Foo")
rsp.headers.add("Foo", "Bar2")
pairs = rsp.headers.pairs()
rsp.headers.delete("Foo")
rsp.headers.dict()

# Manage body of a message
req.body = "foo=bar" # set the body of the message to a string
req.body = b"\x01\x02\x03" # set the body to bytes
bd = req.body # Get the value of the body (always is bytes())
# Same for responses
rsp.body = "foo=bar"
rsp.body = b"\x01\x02\x03"
bd = rsp.body

# Manage POST parameters of a request
params = req.parameters() # Returns a dict of the POST parameters in the form of {"key1": ["val1", "val2"], "key2": ["val3", "val4"]}
[(k, v) for k, v in req.param_iter()] # Iterate through all the key/value pairs of the request parameters
req.set_param("Foo", "Bar") # Set the "Foo" parameter to "Bar"
req.add_param("Foo", "Bar2") # Add a POST parameter to the request allowing duplicates
req.del_param("Foo") # Delete a parameter from the request
# NOTE: Setting a POST parameter will not change the request method to POST

# Managing the cookies of a message
cookie = req.cookies() # Returns an http.cookies.BaseCookie representing the request's cookies
req.set_cookie("foo", "bar") # set a cookie in the request
req.del_cookie("foo") # delete a cookie from the request
[(k, v) for k, v in req.cookie_iter()] # Iterate over the key/value pairs of the cookies in a request
req.set_cookies({"cookie1": "val1", "cookie2": "val2"}) # Set the cookies in the request
req.set_cookies(req2) # Set the requests on req to the cookies in req2
req.add_cookies({"cookie1": "val1", "cookie2": "val2"}) # Add cookies to the request replacing existing values
req.add_cookies(req2) # Add cookies from req2 to the request replacing existing values
# Same for responses
cookie = rsp.cookies()
rsp.set_cookie("foo", "bar")
rsp.del_cookie("foo")
[(k, v) for k, v in rsp.cookie_iter()]
rsp.set_cookies({"cookie1": "val1", "cookie2": "val2"})
rsp.set_cookies(rsp2)
rsp.add_cookies({"cookie1": "val1", "cookie2": "val2"})
rsp.add_cookies(rsp2)

# Manage tags of a request
hastag = ("tagname" in req.tags) # check if a request has a tag
req.tags.add("tagname") # add a tag to a request
req.tags.remove("tagname") # remove a tag from the request
# NOTE: req.tags is a regular set() and you can do whatever you want to it
```

## Macro Arguments

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_macro_args.png)

Both active and intercepting macros can optionally have Guppy prompt for a set of arguments before running. These arguments will be passed as a dict in the `args` variable when calling the relevant function. A macro can request arguments by defining a `get_args` function and returning a list of strings. For example if a macro defines the following `get_args` function:

```python
def get_args():
    return ["foo", "bar"]
```

the proxy will prompt for values for foo and bar. If the user enters "FOOARG" and "BARARG" for the values `args` will have a value of:

```python
{"foo": "FOOARG", "bar": "BARARG"}
```

See below for examples on how to use arguments in macros. If `get_args` is not defined, `None` will be passed in for `args`.

## Active Macros

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_macro_active_in.png)

Active macros are a Python script that define a `run_macro` function that takes in two arguments. A `MacroClient` (as defined in `guppyproxy/macros.py`) and a list of requests (`HTTPRequest` and `HTTPResponse` are defined in `guppyproxy/proxy.py`). The following is an example of a macro that resubmits all of the input requests but adds a new header:

```python
# addheader.py

def get_args():
    return ["header_key", "header_val"]

def run_macro(client, args, reqs):
    for req in reqs:
        client.output("Submitting request to %s..." % req.full_url())
        req.headers.set(args["header_key"], args["header_val"])
        client.submit(req)
        client.output_req(req)
```

Macros such as this can be used for things such as testing auth controls or brute forcing paths/filenames.

## Intercepting Macros

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_macro_int.png)

Intercepting macros are used to look at/modify requests as they pass through the proxy. This is done by defining `mangle_request` and/or `mangle_response`:

```
mangle_request(client, req): Takes in a client and an HTTPRequest and returns an HTTPRequest. The returned HTTPRequest will be sent to the server instead of the original.
mangle_response(client, req, rsp): Takes in a client, HTTPRequest, and HTTResponse and returns an HTTPResponse. The returned HTTPResponse will be sent to the browser instead of the original.
```

As an example, the following macro will ask for a find/replace value. When run, it will set the `session` cookie in the request to `bar` before submitting it to the server and then perform the given find and replace on the body of the response.

```python
# intexample.py

def get_args():
    return ["find", "replace"]

def mangle_request(client, args, req):
    req.set_cookie("session", "bar")
    return req

def mangle_response(client, args, req, rsp):
    rsp.body = rsp.body.replace(args['find'].encode(), args['replace'].encode())
    return rsp
```

# Settings

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_settings.png)

This tab allows you to edit your proxy settings. It lets you select a file to store your history/settings in and configure what ports the proxy listens on. It also allows you to configure an upstream proxy to use. You can add a listener by entering the interface and port into the text boxes and clicking the "+" button. They can be deleted by selecting them from the list and clicking the "-" button.

You can also specify settings for an upstream proxy by checking the "Use Proxy" box, filling out the appropriate info, and clicking "confirm".

## Data Files

Your entire request history and your settings can be stored in a data file on disk. This allows you to save your work for later and even send your work to someone else. You can start a new project with a new data file by clicking the "New" button in the settings tab. Once you do this, your settings, scope, and all the messages that pass through the proxy will be saved to the specified file. You can also load an existing project by using the "Open" button. Finally, you can specify a data file by typing the path into the text box and clicking "Go!"

# Keybindings

Guppy has the following keybindings:

| Key | Action |
|:--------|:------------|
| `Ctrl+J` | Navigate to request list |
| `Ctrl+T` | Navigate to tree view |
| `Ctrl+R` | Navigate to repeater |
| `Ctrl+N` | Navigate to interceptor |
| `Ctrl+D` | Navigate to decoder |
| `Ctrl+U` | Navigate to filter text input |
| `Ctrl+I` | Navigate to filter dropdown input |
| `Ctrl+P` | Navigate to filters and pop most recent filter |
| `Ctrl+Shift+D` | Navigate to decoder and fill with clipboard |
| `Ctrl+Shift+N` | Create new datafile |
| `Ctrl+Shift+O` | Open existing datafile |
