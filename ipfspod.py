#!/usr/bin/env python3
""" Manage IPFS podcasts via a simple command line script. """
from argparse import ArgumentParser
import json
from pprint import pprint
import subprocess
from pathlib import Path
from datetime import datetime
import random
import base64
import os
import git_cmd
import shutil
import re
#import CloudFlare
import ipfshttpclient
from dirsync import sync
import requests

from jinja2 import Environment, FileSystemLoader, select_autoescape
import filetype
from tinydb import TinyDB, Query

parser = ArgumentParser(
    description=f"Publish podcasts on IPFS"
)
subparsers = parser.add_subparsers(help="Command")
parser.set_defaults(command=lambda _: parser.print_help())

#
# ipfspod new: Create a new podcast
#
cmd_new = subparsers.add_parser(
    "new",
    description="Create a new podcast, in a new folder",
    epilog="These fields all fill out a template and are easily changed later,"
           " in particular description should probably be longer than is"
           " conveniently given as an option.")
cmd_new.add_argument(
    "channel_name",
    help="Short channel name with no special characters")
cmd_new.add_argument("--title", help="Longer, human readable channel title")
cmd_new.add_argument(
    "--description",
    help="Detailed channel description, optionally in HTML.")
cmd_new.add_argument("--link", help="Link to the podcast home page")
cmd_new.add_argument(
    "--copyright",
    help="Copyright information (peer-to-peer; not every license makes sense)")
cmd_new.add_argument(
    "--language", default="en",
    help="Language as a two character code,"
         " plus optional variant (e.g. 'en', 'en-US')")
cmd_new.add_argument(
    "--managing-editor", "--author", default="anonymous",
    help="Channel's managing editor: in most cases also the sole author")
cmd_new.add_argument(
    "--ttl", type=int, default=1800,
    help="Recommended time between client refreshes, in seconds")
cmd_new.add_argument(
    "--key",
    help="Don't create a key for this channel: use this key instead")


def run_new(args):
    """ Create a new podcast

        This creates a new directory and fills it with a few standard
        templates, creating a new IPNS key

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
    """
    channel_name = Path(args.channel_name).name
    title = args.title or channel_name.replace("_", " ")
    home = Path('./channels').joinpath(args.channel_name).absolute()
    home.mkdir(parents=True, exist_ok=True)

  
    metadata = dict(
        title=title,
        description=args.description or title,
        link=args.link or "https://ipfs.io/ipns/podcastipfs.andrewtheguy.com",
        copyright=args.copyright or "CC-BY 4.0 Intl.",
        language=args.language or "en",
        managing_editor=args.managing_editor or "anonymous",
        ttl=args.ttl,
        key=''
    )

    print(
        f"Generating a new channel {title} in {home.as_posix()}"
        " with the following properties:"
    )
    pprint(metadata)

    db = TinyDB(home.joinpath("channel.json").as_posix())
    db.truncate()

    db.insert(metadata)




cmd_new.set_defaults(command=run_new)

#
# ipfspod add: Add a new episode to the channel
#

cmd_add = subparsers.add_parser(
    "add",
    description="Add a new episode to a channel's episode list",
    epilog="The channel must be initialized by `ipfspod new`"
)
cmd_add.add_argument("channel", help="Directory for the channel to append to")
cmd_add.add_argument(
    "-t","--title", 
    help="Longer, human readable episode title")
cmd_add.add_argument(
    "-d", "--description",
    help="Detailed episode description, optionally in HTML")
cmd_add.add_argument(
    "-l", "--link", help="Link to a copy of this post, if applicable")
cmd_add.add_argument(
    "-a", "--author", help="Author, if different from managing editor")
cmd_add.add_argument(
    "-c", "--category", nargs="+", default=[],
    help="Category or tag for this post. Conventially nested with '/',"
    " like 'tech/linux/admin'. You can also specify multiple,"
    " e.g. '-c health/fitness health/weight-loss'")
cmd_add.add_argument(
    "-f", "--file", action="append", default=[],
    help="Attach a file to this post. Requires ipfs installed in $PATH")
cmd_add.add_argument(
    "-e", "--enclosure", action="append", nargs=3, default=[],
    metavar=("HASH", "LENGTH_IN_BYTES", "MIMETYPE"),
    help="Attach a file specifying details directly instead of calling ipfs."
         " Use -e multiple times may not be supported by all aggregators.")
cmd_add.add_argument(
    "-s", "--source", help="Link to the feed this was forwarded from, if any")

def get_channel_dir(args):
    return Path('./channels').joinpath(args.channel).absolute()

def run_add(args):
    """ Add a new episode to a channel's episode list

        Requires the channel was initialized by `ipfspod new`

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
    """
    home = get_channel_dir(args)
    channel_db = TinyDB(home.joinpath("channel.json").as_posix())
    channel = channel_db.all()[0]

    client = ipfshttpclient.connect() 

    # Add any videos or audio to IPFS before writing episode metadata
    new_enclosures = []
    for filename in args.file:
        res = client.add(filename)
        file_hash = res['Hash']
        file_len = Path(filename).stat().st_size
        file_type = filetype.guess_mime(filename)
        new_enclosures.append((file_hash, file_len, file_type))
    #print(args.file[0])
    first_filename = os.path.splitext(os.path.basename(args.file[0]))[0]

    # Build the episode metadata JSON object
    episode = dict(
        title=args.title or first_filename,
        description=args.description or args.title or first_filename,
        link=args.link,
        author=args.author or channel['managing_editor'],
        categories=args.category,
        date=datetime.utcnow().strftime(r"%a, %d %b %Y %H:%M:%S +0000"),
        enclosures=[
            # Name the fields and include any we just indexed
            dict(hash=enc[0], len=enc[1], type=enc[2])
            for enc in args.enclosure + new_enclosures
        ],
        # Generates a hash like RLZtAITwyHgorjZ0HYPvl9oYsFFRhIrFhjmZAbbd410=
        # but b64encode creates a bytes() so decode() means convert to str()
        hash=base64.b64encode(
            random.getrandbits(256).to_bytes(32, 'big')
        ).decode(),
        source=args.source
    )

    episode_db = TinyDB(home.joinpath("episodes.json").as_posix())

    episode_db.insert(episode)

    print(f"added {first_filename}")


cmd_add.set_defaults(command=run_add)

#
# ipfspod gen: Generate a new latest_feed.xml
#

cmd_publish = subparsers.add_parser(
    "publish",
    description="Regenerate the RSS feed and update IPNS",
    epilog="Requires the channel was initialized by `ipfspod new`"
)
cmd_publish.add_argument(
    "channel", help="Channel directory (containing metadata.json)")
cmd_publish.add_argument(
    "-n", "--dry-run", action="store_true",
    help="Generate RSS but don't publish it.")


def run_publish(args):
    """ Generate an RSS feed for a podcast

        Requires the channel was initialized by `ipfspod new`

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
        """
        
    home = get_channel_dir(args)
    channel = json.loads(home.joinpath("channel.json").read_text())
    now = datetime.utcnow().strftime(r"%a, %d %b %Y %H:%M:%S +0000")
    episode_db = TinyDB(home.joinpath("episodes.json").as_posix())
    episodes = episode_db.all()

    env = Environment(
        loader=FileSystemLoader(os.path.dirname(os.path.realpath(__file__))),
        autoescape=select_autoescape(['html', 'xml', 'jinja'])
    )
    template = env.get_template("feed_template.xml.jinja")
    feed = template.render(channel=channel, episodes=episodes, now=now)
    dest = f'{git_cmd.PATH_OF_GIT_REPO}/{args.channel}'

    filename = 'feed.xml'

    feed_path = home.joinpath(filename)


    if not args.dry_run:
        # see https://github.com/cloudflare/python-cloudflare#providing-cloudflare-username-and-api-key for configuring api key
        #cf = CloudFlare.CloudFlare()

        print("Publishing. This can take time.")
        # file_hash = (
        #     subprocess
        #     .check_output(["ipfs", "add", "-Q", "-r", home.as_posix()])
        #     .decode()
        #     .strip()
        # )

        git_cmd.git_clone()

        feed_path.write_text(feed)

        # https://github.com/andrewtheguy/podcastsnew
        sync(get_channel_dir(args),dest,'sync',purge=True,create=True)
        

        git_cmd.git_push()

        print(f"podcast published under https://podcasts.planethub.info/{args.channel}/{filename}")

        # subprocess.check_call(
        #     #["ipfs", "name", "publish", "--key", home.name, file_hash]
        # )

        # # cloudflare
        # domain_name = re.sub("[^A-Za-z0-9]","",args.channel)

        # zone_name = 'planethub.info'
        # r = cf.zones.get(params={'name': zone_name})[0]
      
        # zone_id = r['id']
        # record_name = '_dnslink.'+domain_name
        # # DNS records to create
        # new_record = {'name': record_name, 'type':'TXT','content': f'dnslink=/ipfs/{file_hash}'}

        # dns_record = cf.zones.dns_records.get(zone_id, params={'name': record_name + '.' + zone_name })

        # dns_record_id = dns_record[0]['id'] if dns_record else None

        # if dns_record_id:
        #     r = cf.zones.dns_records.put(zone_id, dns_record_id, data=new_record)
        # else:
        #     r = cf.zones.dns_records.post(zone_id, data=new_record)
        

        # print(f"podcast published under https://ipfs.io/ipns/{domain_name}.{zone_name}/{filename}")


cmd_publish.set_defaults(command=run_publish)

from subprocess import Popen, PIPE, DEVNULL
from multiprocessing import Pool
import glob,sys
from concurrent.futures import ThreadPoolExecutor

def download_with_curl(gateway,hash):
    #print('---')
    #print(url)
    #print('...')
    url = f"https://{gateway}/ipfs/{hash}"
    print('downloading ' + url)

    # or api way
    #url = f"https://{gateway}/api/v0/cat?arg={hash}"
    Path(f"./test/{gateway}").mkdir(parents=True, exist_ok=True)


    with open(f"./test/{gateway}/{hash}.log", "wb") as f:
        p = Popen(["curl", url] , stdout=DEVNULL, stderr=f)
        # or api way
        #p = Popen(["curl", '-X','POST', url] , stdout=DEVNULL, stderr=f)
        p.wait() # wait for process to finish; this also sets the returncode variable inside 'res'
        #print(p.returncode)
        if p.returncode != 0:
            #print('chafa')
            raise Exception(f"{url} download failed, exit code {p.returncode}")

cmd_test_gateway = subparsers.add_parser(
    "test_gateway",
    description="test downloading episodes through a gateway",
    epilog="test_gateway"
)
cmd_test_gateway.add_argument(
    "channel", help="Channel directory (containing metadata.json)")
# cmd_test_gateway.add_argument(
#     "gateway", help="gateway domain")
def run_test_gateway(args):
    """
    test downloading through gateways
    """
    if __name__ == '__main__':
        gateways = [
            'ipfs.io', # the same one first
            'dweb.link',
            'cloudflare-ipfs.com',
            'gateway.ravenland.org',
            'hardbin.com',
            'astyanax.io',
        ]

        home = get_channel_dir(args)
        episode_db = TinyDB(home.joinpath("episodes.json").as_posix())
        episodes = episode_db.all()
        #print(episodes)

        #arr = [(gateway,episode['enclosures'][0]['hash']) for gateway in gateways for episode in episodes]

        #one by one
        for gateway in gateways:
            arr = [(gateway, episode['enclosures'][0]['hash']) for episode in episodes]
            with Pool(5) as p:
                r = p.starmap_async(download_with_curl, arr)
                r.get()

        # cmds_list = [["curl", f"https://{args.gateway}/ipfs/{episode['enclosures'][0]['hash']}"] for episode in episodes]
        #
        # procs_list = [Popen(cmd, stdout=DEVNULL, stderr=sys.stderr) for cmd in cmds_list]
        #
        # for proc in procs_list:
        #     proc.wait()




cmd_test_gateway.set_defaults(command=run_test_gateway)

# Finally, use the new parser
all_args = parser.parse_args()
# Invoke whichever command is appropriate for the arguments
all_args.command(all_args)
