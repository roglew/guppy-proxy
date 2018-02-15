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

# Settings

![screenshot](https://github.com/roglew/guppy-static/blob/master/ss_settings.png)

This tab allows you to edit your proxy settings. It lets you select a file to store your history/settings in and configure what ports the proxy listens on. It also allows you to configure an upstream proxy to use. You can add a listener by entering the interface and port into the text boxes and clicking the "+" button. They can be deleted by selecting them from the list and clicking the "-" button.

You can also specify settings for an upstream proxy by checking the "Use Proxy" box, filling out the appropriate info, and clicking "confirm".

## Data Files

Your entire request history and your settings can be stored in a data file on disk. This allows you to save your work for later and even send your work to someone else. You can start a new project with a new data file by clicking the "New" button in the settings tab. Once you do this, your settings, scope, and all the messages that pass through the proxy will be saved to the specified file. You can also load an existing project by using the "Open" button. Finally, you can specify a data file by typing the path into the text box and clicking "Go!"
