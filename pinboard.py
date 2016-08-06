# Keypirinha | A semantic launcher for Windows | http://keypirinha.com

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_api
import os
import datetime
import urllib
import urllib.request
import json

class Bookmark():
    def __init__(self, tags, label, url):
        self.tags = tags
        self.label = label.strip() if isinstance(label, str) else ""
        self.url = url.strip() if isinstance(url, str) else ""

        self.scheme = None
        self.empty_label = False
        self.is_auth = False
        self.pretty_url = self.url

        try:
            parsed = urllib.parse.urlparse(self.url)

            self.scheme = parsed.scheme

            if parsed.username or parsed.password:
                self.is_auth = True

            self.pretty_url = parsed.hostname + parsed.path
        except Exception:
            pass

        if not self.label:
            self.empty_label = True
            self.label = self.pretty_url

class Pinboard(kp.Plugin):
    """Launch Pinboard bookmarks."""

    DEFAULT_ITEM_LABEL_FORMAT = "Pinboard: {label} ({tags})"
    
    api_base = "https://api.pinboard.in/v1/posts/all"
    api_format = "json"
    api_file = "pinboard.json"
    api_token = None
    bookmark_file = None
    
    item_label_format = DEFAULT_ITEM_LABEL_FORMAT
    keep_empty_names = True
    keep_auth_url = True
    force_new_window = None
    force_private_mode = None

    def __init__(self):
        super().__init__()
        self._debug = False

    def on_start(self):
        self.dbg("On Start")
        self._read_config()

    def on_catalog(self):
        self.dbg("On Catalog")
        self._create_cache()
        self._download_bookmarks()

        bookmarks = []
        bookmarks = self._list_bookmarks()
        
        catalog = []
        for b in bookmarks:
                if not b.label or not b.url:
                    continue
                if b.empty_label and not self.keep_empty_names:
                    continue
                if b.is_auth and not self.keep_auth_url:
                    continue
                if "script" in b.scheme.lower(): # javascript, vbscript, ...
                    continue
                catalog.append(self.create_item(
                    category=kp.ItemCategory.URL,
                    label=self.item_label_format.format(
                                    label=b.label, tags=b.tags),
                    short_desc="",
                    target=b.url,
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.NOARGS))

        self.set_catalog(catalog)
        self.info("Referenced {} bookmark{}".format(len(catalog), "s"[len(catalog)==1:]))

    def on_execute(self, item, action):
        if action:
            kpu.execute_default_action(self, item, action)
        else:
            kpu.web_browser_command(
                private_mode=self.force_private_mode,
                new_window=self.force_new_window,
                url=item.target(),
                execute=True)

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.on_catalog()

    def _read_config(self):
        self.dbg("Read Config")
        settings = self.load_settings()
        
        self.api_token = settings.get("api_token", "main", None)
        self.item_label_format = settings.get("item_label_format", "main", self.DEFAULT_ITEM_LABEL_FORMAT)
        self.keep_empty_names = settings.get_bool("keep_empty_names", "main", True)
        self.keep_auth_url = settings.get_bool("keep_auth_url", "main", True)
        self.force_new_window = settings.get_bool("force_new_window", "main", None)
        self.force_private_mode = settings.get_bool("force_private_mode", "main", None)
    
    def _create_cache(self):
        plugin_directory = self.get_package_cache_path(create=True)
        self.bookmark_file = plugin_directory + "\\" + self.api_file
    
    def _download_bookmarks(self):
        self.dbg("Download Bookmarks")

        if len(self.api_token) == 0:
            self.info("API token is not valid.")

        self.api_url = self.api_base + "?auth_token=" + self.api_token + "&format=" + self.api_format
       
        if os.path.isfile(self.bookmark_file):
            today = datetime.datetime.today()
            file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.bookmark_file))
            delta = today - file_modified
            if delta.seconds > (4 * 60 * 60): # if file is older than 4 hours, download a new copy
                try:
                    response = urllib.request.urlretrieve (self.api_url, self.bookmark_file)
                except:
                    self.info("Pinboard website unreachable.")
        else:
            try:
                response = urllib.request.urlretrieve (self.api_url, self.bookmark_file)
            except:
                self.info("Pinboard website unreachable.")
       
    def _list_bookmarks(self):
        self.dbg("List Bookmarks")
        
        if not os.path.isfile(self.bookmark_file):
            self._download_bookmarks()
        
        with open(self.bookmark_file) as data_file:
            bookmark_data = json.load(data_file)
        
        bookmarks = []
        for bookmark in bookmark_data:
            tags = bookmark['tags']
            toread = None
            if bookmark['toread'] == "yes":
                if len(tags) == 0:
                    tags = "#toread"
                else:
                    tags = "#toread " + tags
            bookmarks.append(Bookmark(tags, bookmark['description'], bookmark['href']))
            
        return bookmarks