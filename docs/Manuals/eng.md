# Gemini API Key Setup Guide

## 1. Create a Google Account

If you already have a Gmail account, you can skip this step.

Recommended:

* use a regular personal Google account
* enable a VPN during registration (set to a foreign country or don't use it if you're in one)
* use a supported region



## 2. Open Google AI Studio

Go to:

[Google AI Studio](https://aistudio.google.com)

Sign in to your Google account and accept the Terms of Service.



## 3. Create an API Key

Open the API keys page:

[Gemini API Keys](https://aistudio.google.com/app/apikey)

Click:

```text
Create API Key
```

or:

```text
Create API key in new project
```



## 4. Copy Your API Key

After creation, you will receive a key that looks like:

```text
AIzaSy...
```

Copy and save it somewhere secure.

Do not share your API key with anyone.



## 5. Add the Key to the Bot

In the bot, open:

```text
Settings -> Add API Key
```

Send your API key and save it.

The bot will automatically validate the key.



# Important

## Never:

* publish your API key
* send your API key to other people


# Possible Errors

### “Invalid API key”

Usually means:

* the key was copied incorrectly
* extra spaces were added accidentally
* the key was deleted



### “Region not supported”

Gemini is not available in all countries.

Try:

* changing your VPN location
* using another Google account
* changing your account region



### “Rate limit exceeded”

You have exceeded the free API limits.

Usually it is enough to:

* wait a few minutes
* try again later



# How to Remove the API Key

You can remove the key at any time either in the bot or directly here:

```text
Settings -> Remove API Key
```

[Google AI Studio API Keys](https://aistudio.google.com/app/apikey)

After deletion, the bot will no longer be able to use this key.
