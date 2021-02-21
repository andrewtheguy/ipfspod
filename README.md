# IPFSPod: Video Channels on IPFS
Publish your own content in a channel on IPFS,
using RSS and peer to peer file sharing to get an effect similar to channels
on video streaming websites.

# Install IPFS and IPFSPod
First, you need to install [Interplanetary Filesystem](ipfs.io). It powers the
whole show and without it you have nothing.

```sh
# Make sure ipfs api is working, otherwise start ipfs
curl -X POST http://127.0.0.1:5001/api/v0/version

#install dependencies
pipenv install

# run shell
pipenv shell
```

# Create a new channel
If you don't already have a podcast, create one.
The name needs to be pretty short, with no special characters, as it's used in
a lot of contexts. If you want something fancier, you can edit the displayed
parts in a moment.

```sh
./ipfspod.py new isnt_nature_neat
```

# Add an episode to your channel
Adding a new episode is pretty painless, but you can make it as detailed as you
want.

> We're assuming you're in the channel directory. If not, then change `.`
> to that directory

```sh
./ipfspod.py add isnt_nature_neat \
    -f the_cool_lizard.webm \
    -t 'Found a lizard in the back yard, neat!' #optional

# Most RSS metadata is supported, like --link, --source, and --author

# loop through folder
for f in /Users/it3/tmp/add/*.mp3; do ./ipfspod.py add isnt_nature_neat -f $f; done
```

# Publish your channel

Once you have added your episode, or a few if you want, regenerate and publish
your new feed to git!

```sh
./ipfspod.py publish isnt_nature_neat
```
<!---
Once you have added your episode, or a few if you want, regenerate and publish
your new feed with the cloudflare API token!

```sh
CF_API_KEY=token ./ipfspod.py publish isnt_nature_neat

# You can also use -n to check the results before actually publishing
```
--->

# Test download
```
./ipfspod.py test_gateway isnt_nature_neat
```