import io
import os

from pydatpiff.utils.filehandler import File, Tmp, get_human_readable_file_size
from pydatpiff.utils.utils import Object, Select, ThreadQueue, threader_wrapper

from .backend.audio.player import Player
from .backend.mediasetup import Album, Mp3
from .errors import MediaError
from .frontend import screen
from .mixtapes import Mixtapes
from .urls import Urls
from .utils.request import Session

Verbose = screen.Verbose


class Media:
    """A media player that control the songs selected from Mixtapes"""

    player = None

    def __init__(self, mixtapes=None, pre_select=None, player="mpv", **kwargs):
        """
        Initialize a media player and load all mixtapes.

        Args:
            mixtapes (instance class) -- pydatpiff.Mixtapes instance (default: {None})
            pre_select (Integer,String) --  pre-selected mixtape's album, artist,or mixtapes.
                    See media.setMedia for more info (default: None - Optional)

        Raises:
            MediaError: Raises MediaError if mixtapes is not a subclass of pydatpiff.Mixtapes.
        """
        self.__setup(player)
        self._album_cover = None
        self.bio = None
        self._Mp3 = None
        self.url = None
        self.uploader = None
        self._session = Session()
        self.mixtapes = mixtapes
        self._artist_name = None
        self._album_name = None
        self._current_index = None
        self._selected_song = None
        self.__cache_storage = {}

        # Check if mixtape is valid
        self.__is_valid_mixtape(mixtapes)

        Verbose("Media initialized")

        if pre_select:  # Run setMedia with argument here
            # This step is optional for users, but can save an extra setup
            # when selecting an album in setMedia.
            self.setMedia(pre_select)

    def __str__(self):
        album_name = self._album_name
        if album_name:
            return "{} Mixtape".format(album_name)
        return str(self.mixtapes)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.mixtapes.__class__)

    def __len__(self):
        if hasattr(self, "songs"):
            return len(self.songs)
        else:
            return 0

    def __setup(self, player=None):
        if not hasattr(self, "__temp_file"):
            Tmp.removeTmpOnStart()
            self.__temp_file = Tmp.create()

        # Set the initial player. fallback to mpv if not specified
        player = player or "mpv"
        self.player = Player.getPlayer(player)

    def _select(self, choice):
        """
        Queue and load  a mixtape to media player.
                            (See pydatpiff.media.Media.setMedia)

        :param: choice - (int) user selection by indexing an artist name or album name
                            (str)
        """
        # Map user selection according to the incoming datatype.
        # We map an integer to an artist and str to a mixtape.
        if hasattr(self, "mixtapes"):
            if isinstance(choice, int):
                selection = Select.get_index(choice, options=self.mixtapes.artists)
            else:
                options = [self.mixtapes.artists, self.mixtapes.mixtapes]
                selection = Select.get_index_of(choice, options=options)
            return selection

    def setMedia(self, mixtape):  # noqa
        """
        Initialize and set the Mixtape to Media Player.
        A pydatpiff.mixtapes.Mixtape's album will be load to the media player.

        Args:
            selection - pydatpiff.Mixtapes album's name or artist's name.
                int - will return the Datpiff.Mixtape artist at that index.
                str - will search for an artist from Mixtapes.artists (default)
                    or album from Mixtapes.album.

                See pydatpiff.mixtape.Mixtapes for a mixtape album or artist selection
        """

        # Mixtape's class will handle errors and None value

        mixtape_index = self._select(mixtape)

        # set up all Album's Info
        total_mixtape = len(self.mixtapes) - 1
        if mixtape_index > total_mixtape:
            mixtape_index = total_mixtape

        # set Media's Mixtapes object attributes
        url = self.mixtapes._links[mixtape_index]  # noqa
        self.url = "".join((Urls.datpiff["base"], url))

        self.artist = self.mixtapes.artists[mixtape_index]
        self.album_cover = self.mixtapes.album_covers[mixtape_index]

        # set Media's Album detail attributes
        self.album = Album(url)
        self._Mp3 = Mp3(self.album)

        # get the album's uploader and bio
        self.uploader = getattr(self.album, "uploader", "unknown uploader")
        self.bio = getattr(self.album, "uploader", "no bio")
        Verbose("Setting Media to %s - %s" % (self.artist, self.album))

    def __is_valid_mixtape(self, instance):
        """Verify subclass is an instance of mixtapes' class

        Args:
            instance {instance class} -- pydatpiff's Mixtapes instance

        Returns:
            Boolean -- True or False if instance is subclass of pydatpiff Mixtape class
        """
        if not instance:
            raise MediaError(1)

        if not issubclass(instance.__class__, Mixtapes):
            raise MediaError(2, '"mixtape" must be Mixtapes object ')

    def find_song(self, name):
        """
         Search through all mixtapes songs and return all songs
         with song_name

        Args:
            song_name {str} -- song to search for.

        Returns:
            tuple -- returns a tuple containing mixtapes data (index,artist,album) from search.
        """

        # NOTE: Take a look at this video by James Powell
        # https://www.youtube.com/watch?v=R2ipPgrWypI&t=1748s at 55:00.

        song_name = Object.strip_and_lower(name)
        Verbose("\nSearching for song: %s ..." % song_name)
        links = self.mixtapes.links
        links = list(enumerate(links, start=1))
        results = ThreadQueue(Album.lookup_song, links).execute(song_name)
        if not results:
            Verbose("No song was found with the name: %s " % song_name)
        results = Object.remove_none_value(results)
        return results

    def __index_of_song(self, select):
        """
        Parse all user input and return the correct song index.
        :param select: -  Media.songs name or index of Media.songs
               datatype: int: must be numerical
                         str: artist,mixtape, or song name
        """
        try:
            if isinstance(select, int):
                return Select.get_index(select, self.songs)
            return Select.get_index_of(select, self.songs)
        except MediaError:
            raise MediaError(5)

    @property
    def artist(self):
        """Return the current artist name."""
        if not hasattr(self, "_artist_name"):
            self._artist_name = None
        return self._artist_name

    @artist.setter
    def artist(self, name):
        self._artist_name = name

    @property
    def album(self):
        """Return the current album name."""
        if not hasattr(self, "_album_name"):
            self._album_name = None
        return self._album_name

    @album.setter
    def album(self, name):
        self._album_name = name

    @property
    def album_cover(self):
        if hasattr(self, "_album_cover"):
            return self._album_cover

    @album_cover.setter
    def album_cover(self, url):
        self._album_cover = url

    @property
    def songs(self):
        """Return all songs from album."""
        if not hasattr(self, "_Mp3"):
            extra_message = '\nSet media by calling -->  Media.setMedia("some_mixtape_name")'
            raise MediaError(3, extra_message)
        return self._Mp3.songs

    @property
    def mp3_urls(self):
        """Returns all parsed mp3 url"""
        return list(self._Mp3.mp3_urls)

    def show_songs(self):
        """Pretty way to Print all song names"""
        try:
            songs = self.songs
            [Verbose("%s: %s" % (a + 1, b)) for a, b in enumerate(songs)]
        except TypeError:
            Verbose("Please set Media first\nNo Artist name")

    @property
    def song(self):
        """Returns the current song set by user."""
        return self._selected_song

    @song.setter
    def song(self, name):
        """
        Set current song
        name - name of song or song's index
        """
        index = self.__index_of_song(name)
        if index is not None:
            self._selected_song = self.songs[index]
            self._current_index = index
        else:
            Verbose("\n\t song was not found")

    def _cache_song(self, song, content):
        """
        Preserve the data from song and store it for future calls.
         This prevents calling the requests function again for the same song.
         Each data from a song will be stored in __cache_storage for future access.

        Args:
            song (str):  name of song
            content (byte): song's audio content
        """
        song = "-".join((self.artist, song))
        try:
            self.__cache_storage[song] = content
        except MemoryError:
            self.__cache_storage = {}

    def _retrieve_song_from_cache(self, song):
        """Retrieve song's audio content from cache
        Args:
            song (str): name of song

        Returns:
            Http response : A http response containing the song's audio contents.
        """
        requested_song = "-".join((self.artist, song))
        if hasattr(self, "__cache_storage"):
            if requested_song in self.__cache_storage:
                return self.__cache_storage.get(requested_song)

    def _write_audio(self, track):
        """Write mp3 audio content to IO Bytes stream.
        Args:
            track (int,string): Name or index of song.

        Returns:
            BytesIO: A file-like API for reading and writing bytes objects.
        """

        selection = self.__index_of_song(track)
        if selection is None:
            raise MediaError("Song not found")

        self.__song_index = selection
        link = self.mp3_urls[selection]

        song_name = self.songs[selection]
        self.song = selection + 1

        # Retrieve song's content in cached
        response = self._retrieve_song_from_cache(song_name)
        if not response:
            response = self._session.method("GET", link)
            self._cache_song(song_name, response)

        return io.BytesIO(response.content)

    @property
    def autoplay(self):
        """Continuously play song from current mixtape album."""
        if hasattr(self, "_auto_play"):
            self.player._media_autoplay = self._auto_play
            return self._auto_play

    @autoplay.setter
    def autoplay(self, auto=False):
        """Sets the autoplay function.

        auto - disable or enable autoplay
                 datatype: boolean
                 default: False
        """
        self._auto_play = auto  # noqa
        self._continous_play()
        if auto:
            Verbose("\t----- AUTO PLAY ON -----")
        else:
            Verbose("\t----- AUTO PLAY OFF -----")

    @threader_wrapper
    def _continous_play(self):
        """
        Automatically play each song from Album when autoplay is enable.
        """
        if self.autoplay:
            total_songs = len(self)
            if not self.song:
                Verbose("Must play a song before setting autoplay")
                return

            track_number = self.__index_of_song(self.song) + 2
            if track_number > total_songs:
                Verbose("AutoPlayError: The current track is the last track on the album")
                self.autoplay = False
                return

            while self.autoplay:
                current_track = self.__index_of_song(self.song) + 1
                stopped = self.player._state.get("stopped")  # noqa
                if stopped:
                    next_track = current_track + 1

                    if next_track > total_songs:
                        Verbose("No more songs to play")
                        self.autoplay = False
                        break

                    Verbose("Loading next track")
                    Verbose("AUTO PLAY ON")
                    self.play(next_track)
                    while self.player._state["stopped"]:  # noqa
                        pass

    def play(self, track=None, demo=False):
        """Play selected mixtape's track

        Args:
            track (int,string)- name or index of song.
            demo (bool, options) - True: demo buffer of song (default: False).
                False: play full song
        """
        if not track:
            Verbose("\n\t -- No song was entered --")
            return

        if self.player is None:
            extended_msg = "Audio player is incompatible with device"
            raise MediaError(6, extended_msg)

        if isinstance(track, int):
            if track > len(self):
                track = len(self)
        else:
            track = self.__index_of_song(track) + 1

        try:
            content = self._write_audio(track).read()
        except:
            Verbose("\n\t-- No song was found --")
            return

        song_name = self.songs[self.__song_index]
        track_size = len(content)
        # play demo or full song
        if not demo:  # demo whole song
            chunk = content
            buffer = int(track_size)
        else:  # demo partial song
            buffer = int(track_size / 5)
            start = int(buffer / 5)
            chunk = content[start : buffer + start]
        size = get_human_readable_file_size(buffer)

        # write song to file
        File.write_to_file(self.__temp_file.name, chunk, mode="wb")

        # display message to user
        screen.display_play_message(self.artist, self.album, song_name, size, demo)

        song = " - ".join((self.artist, song_name))
        self.player.set_track(song, self.__temp_file.name)
        self.player.play  # noqa - play song is a property of the player class

    def download(self, track=None, rename=None, output=None):
        """
        Download song from Datpiff

        Args:
            track (int,string) - name or index of song type(str or int)
            output (string) - location to save the song (optional)
            rename (string) - rename the song (optional)
                default will be song's name
        """
        selection = self.__index_of_song(track)
        if selection is None:
            return

        # Handles paths
        output = output or os.getcwd()
        if not File.is_dir(output):
            raise FileNotFoundError("Invalid directory: %s" % output)

        song = self.songs[selection]

        # Handles song's renaming
        if rename:
            title = rename.strip() + ".mp3"
        else:
            title = " - ".join((self.artist, song.strip() + ".mp3"))

        title = File.standardize_name(title)
        song_name = File.join(output, title)

        content = self._write_audio(song).read()
        size = get_human_readable_file_size(len(content))
        File.write_to_file(song_name, content, mode="wb")
        screen.display_download_message(title, size)

    def download_album(self, output=None):
        """Download all tracks from Mixtape.

        Args:
            output ([type], optional): path to save mixtape.(default: current directory)
        """
        if not output:
            output = os.getcwd()
        elif not os.path.isdir(output):
            Verbose("Invalid directory: %s" % output)
            return

        formatted_title = " - ".join((self.artist, self.album))
        title = File.standardize_name(formatted_title)
        filename = File.join(output, title)

        # make a directory to store all the album's songs
        if not os.path.isdir(filename):
            os.mkdir(filename)
        ThreadQueue(self.download, self.songs, filename).execute()
        Verbose("\n%s %s saved" % (self.artist, self.album))
