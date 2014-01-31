mootip-imgur-single
===================

A digital currency tipping bot for Imgur. This variant of the bot supports a single currency.

**Requirements**

MongoDB.
Python 3.3, it should work with Python 3 in general however.
PyMongo.

**How To Run**

1. Open `config.json` and set your client ID and secret ID.

2. `python moo.py authorize`

This will give you a URL to visit to retrieve a PIN. Do this from the account you want the bot to run from. You'll get a PIN.

3. `python moo.py authorize <pin>`

This will give you an access token and a refresh token, populate the fields in config.json with this information.

4. `python moo.py`

And done. :-)

**How To Use**

Message the "bot" with help, register or withdraw <address>

**Issues**

Verifying in thread... the only issue is that the comment API has some serious rate limiting in place.

API limits. Even with the Imgur client ID whitelisted, there is still an IP limit (quite a harsh one, 1k per hour). To get around this, you'll need to sign up for a premium API subscription with Mashape - which is fairly cheap. If you want to just try this out, open up Factory.py and change the API_URL from Mashape to Imgur :-). You will also need to update the `X-Mashape-Authorization` headers in Factory.py