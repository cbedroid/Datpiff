from unittest import TestCase
from unittest.mock import Mock

from pydatpiff import mixtapes
from pydatpiff.errors import MixtapesError
from tests.test_utils import BaseTest


class TestMixtapes(BaseTest, TestCase):
    def setUp(self):
        content = self.get_request_content("mixtape")
        method = mixtapes.Session.method = Mock(autospec=True)
        method.return_value = self.mocked_response(content=content)
        self.mix = mixtapes.Mixtapes()

    def test_mixtapes_default_category_was_set(self):
        # test category was set by default
        mix_category = self.mix._selected_category
        self.assertEqual(mix_category, "hot")

    def test_mixtape_mixtapes_were_set(self):
        mixtapes = self.mix.mixtapes
        total_mixtapes = len(mixtapes or [])
        self.assertGreater(total_mixtapes, 0)

    def test_mixtape_artists_were_set(self):
        artists = self.mix.artists
        total_artists = len(artists or [])
        self.assertGreater(total_artists, 0)

    def test_mixtape_links_were_set(self):
        links = self.mix.links
        total_links = len(links or [])
        self.assertGreater(total_links, 0)

    def test_mixtape_views_were_set(self):
        views = self.mix.views
        total_views = len(views or [])
        self.assertGreater(total_views, 0)

    def test_mixtape_album_cover_were_set(self):
        album_covers = self.mix.album_covers
        total_covers = len(album_covers or [])
        self.assertGreater(total_covers, 0)

    def test_mixtape_attributes_size_maps_to_artist_attribute_size(self):
        mixtapes_attributes = ["mixtapes", "links", "views", "album_covers"]
        mix = self.mix
        artist_length = len(mix.artists)

        for attr in mixtapes_attributes:
            obj = getattr(mix, attr, [])
            if not obj:
                raise AttributeError("Mixtape does not have attribute: {}".format(obj))
            attr_length = len(obj)
            self.assertEqual(artist_length, attr_length)

    def test_mixtapes_includes_correct_mixtape(self):
        test_mixtape = self.mixtape_list[0]
        mixtapes = self.mix.mixtapes
        self.assertIn(test_mixtape, mixtapes)

        mixtape_name = mixtapes[mixtapes.index(test_mixtape)]
        self.assertEquals(mixtape_name, "A Gangsta's Pain: Reloaded")

    def test_artists_includes_correct_artist(self):
        test_artist = self.artist_list[0]
        artists = self.mix.artists
        self.assertIn(test_artist, artists)

        artist_name = artists[artists.index(test_artist)]
        self.assertEquals(artist_name, "Moneybagg Yo")


class TestMixtapes_Search(BaseTest, TestCase):
    def setUp(self):
        content = self.get_request_content("mixtape_search")
        method = mixtapes.Session.method = Mock(autospec=True)
        method.return_value = self.mocked_response(content=content)
        search = self.mixtape_search_parameter
        self.mix = mixtapes.Mixtapes(**search)

    def test_mixtape_validate_search_method(self):
        with self.assertRaises(MixtapesError):
            # test validate_search minimum character raise MixtapesError
            self.mix.validate_search("ab", min_characters=3)

            # test validate search expected type throws error
            #  when user input is not entered
            self.mix.validate_search(None, expected=dict)

        # test validate search strips whitespace
        result = self.mix.validate_search("abcd    ", expected=str)
        self.assertEquals(result, "abcd")