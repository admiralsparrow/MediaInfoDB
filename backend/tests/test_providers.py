import pytest

from app.services.providers import PROVIDERS, parse_provider, _alias_to_canonical, _all_tokens


class TestProvidersMapping:
    def test_all_canonicals_map_to_themselves(self):
        for canonical in PROVIDERS:
            assert _alias_to_canonical[canonical] == canonical

    def test_all_aliases_map_to_their_canonical(self):
        for canonical, aliases in PROVIDERS.items():
            for alias in aliases:
                assert _alias_to_canonical[alias] == canonical

    def test_no_duplicate_aliases_across_providers(self):
        seen: dict[str, str] = {}
        for canonical, aliases in PROVIDERS.items():
            for token in [canonical] + aliases:
                if token == canonical and token in seen and seen[token] == canonical:
                    continue
                assert token not in seen, (
                    f"'{token}' appears under both '{seen[token]}' and '{canonical}'"
                )
                seen[token] = canonical

    def test_alias_not_same_as_own_canonical(self):
        for canonical, aliases in PROVIDERS.items():
            for alias in aliases:
                if alias == canonical:
                    pytest.fail(
                        f"'{canonical}' lists itself as an alias — remove it from the alias list"
                    )

    def test_tokens_sorted_longest_first(self):
        for a, b in zip(_all_tokens, _all_tokens[1:]):
            assert len(a) >= len(b)


class TestParseProvider:
    @pytest.mark.parametrize(
        "filename, expected",
        [
            # Canonical codes in typical scene-style filenames
            ("Show.S01E01.2160p.AMZN.WEB-DL.DDP5.1.H.265-GROUP", "AMZN"),
            ("Movie.2024.1080p.NF.WEB-DL.DDP5.1.Atmos.H.264-GROUP", "NF"),
            ("Show.S02E03.720p.DSNP.WEB-DL.DD5.1.H.264-GROUP", "DSNP"),
            ("Movie.2023.2160p.HMAX.WEB-DL.DDP5.1.HDR.HEVC-GROUP", "HMAX"),
            ("Show.S01E01.1080p.ATVP.WEB-DL.DDP5.1.H.265-GROUP", "ATVP"),
            ("Show.S01E01.1080p.PCOK.WEB-DL.DDP5.1.H.264-GROUP", "PCOK"),
            ("Show.S01E01.1080p.PMTP.WEB-DL.DDP5.1.H.264-GROUP", "PMTP"),
            ("Show.S01E01.1080p.CRAV.WEB-DL.DDP5.1.H.264-GROUP", "CRAV"),
            # Aliases resolve to canonical
            ("Show.S01E01.1080p.Amazon.WEB-DL.H.264-GROUP", "AMZN"),
            ("Show.S01E01.1080p.Netflix.WEB-DL.H.264-GROUP", "NF"),
            ("Movie.2024.DisneyPlus.WEB-DL.H.265-GROUP", "DSNP"),
            ("Show.S01E01.HBOMax.WEB-DL.DDP5.1.H.264-GROUP", "HMAX"),
            ("Show.S01E01.AppleTV+.WEB-DL.H.265-GROUP", "ATVP"),  # note: + is escaped in regex
            ("Show.S01E01.Peacock.WEB-DL.DDP5.1.H.264-GROUP", "PCOK"),
            ("Show.S01E01.Paramount+.WEB-DL.H.264-GROUP", "PMTP"),
            ("Show.S01E01.CraveTV.WEB-DL.H.264-GROUP", "CRAV"),
            ("Show.S01E01.Crunchyroll.WEB-DL.H.264-GROUP", "CR"),
            ("Show.S01E01.Fandango.WEB-DL.H.264-GROUP", "FNDG"),
            ("Show.S01E01.FAND.WEB-DL.H.264-GROUP", "FNDG"),
            # Codes with empty alias lists
            ("Show.S01E01.HULU.WEB-DL.H.264-GROUP", "HULU"),
            ("Show.S01E01.HBO.WEB-DL.DDP5.1.H.264-GROUP", "HBO"),
            ("Show.S01E01.MAX.WEB-DL.DDP5.1.H.264-GROUP", "MAX"),
            ("Show.S01E01.PBS.WEB-DL.H.264-GROUP", "PBS"),
        ],
    )
    def test_known_providers(self, filename: str, expected: str):
        assert parse_provider(filename) == expected

    @pytest.mark.parametrize(
        "filename",
        [
            "Movie.2024.1080p.BluRay.x264-GROUP",
            "Movie.2024.2160p.UHD.Blu-ray.Remux.HEVC.DTS-HD-GROUP",
            "random_home_video.mkv",
            "",
        ],
    )
    def test_no_provider_returns_none(self, filename: str):
        assert parse_provider(filename) is None

    def test_ma_matches_in_dts_hd_context(self):
        # MA (MoviesAnywhere) is a short token that can match in audio codec strings
        # where it's dot-delimited. This documents current behavior.
        assert parse_provider("Movie.DTS-HD.MA.7.1-GROUP") == "MA"

    def test_word_boundary_prevents_substring_match(self):
        assert parse_provider("REFORMATTED.mkv") is None
        assert parse_provider("SNOWFALL.S01E01.mkv") is None

    def test_word_boundary_allows_dot_delimited(self):
        assert parse_provider("Show.NF.WEB-DL.mkv") == "NF"

    def test_word_boundary_allows_hyphen_delimited(self):
        assert parse_provider("Show-NF-WEB-DL.mkv") == "NF"

    def test_word_boundary_allows_space_delimited(self):
        assert parse_provider("Show NF WEB-DL.mkv") == "NF"

    def test_longer_token_wins_over_shorter(self):
        assert parse_provider("Show.HMAX.WEB-DL.mkv") == "HMAX"
        assert parse_provider("Show.CCGC.WEB-DL.mkv") == "CCGC"

    def test_first_match_in_string_wins(self):
        result = parse_provider("Show.AMZN.NF.WEB-DL.mkv")
        assert result == "AMZN"

    @pytest.mark.parametrize(
        "alias, canonical",
        [
            ("AmazonPrime", "AMZN"),
            ("NFLX", "NF"),
            ("DSN+", "DSNP"),
            ("APTV", "ATVP"),
            ("MGM+", "EPIX"),
            ("YouTubePremium", "RED"),
            ("IMDBtv", "FREE"),
            ("ITVX", "ITV"),
        ],
    )
    def test_less_common_aliases(self, alias: str, canonical: str):
        filename = f"Show.S01E01.1080p.{alias}.WEB-DL.H.264-GROUP"
        assert parse_provider(filename) == canonical
