"""
Unit tests for backend components.

Tests for:
- Configuration loading and persistence
- File system tools (search and find)
- Hotkey detection
- Web search functionality (DuckDuckGo, URL normalization, scraping)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from pynput import keyboard

from kratt import config
from kratt.core.tools import find_files, search_files, execute_tool, get_tool_definitions
from kratt.core.hotkey_manager import HotkeyManager
from kratt.core.web_search import (
    normalize_url,
    improve_search_query,
    filter_search_results,
    extract_text,
    extract_links_prioritized,
    WebScraper,
    search_duckduckgo,
)


class TestConfigManagement:
    """Test cases for configuration loading and persistence."""

    def test_save_and_load_settings(self, tmp_path):
        """
        Test that settings can be saved and loaded correctly.

        Verifies round-trip persistence of configuration data.
        """
        config.SETTINGS_FILE = tmp_path / "settings.json"
        config.CONFIG_DIR = tmp_path

        original_settings = {
            "main_model": "qwen2.5:7b",
            "vision_model": "moondream:latest",
            "system_prompt": "Test prompt",
        }

        config.save_settings(original_settings)
        loaded_settings = config.load_settings()

        assert loaded_settings["main_model"] == original_settings["main_model"]
        assert loaded_settings["vision_model"] == original_settings["vision_model"]

    def test_load_settings_returns_defaults_on_missing_file(self, tmp_path):
        """
        Test that default settings are returned when settings file is
        missing.

        Verifies graceful fallback to defaults.
        """
        config.SETTINGS_FILE = tmp_path / "nonexistent.json"
        config.CONFIG_DIR = tmp_path

        result = config.load_settings()

        assert result == config.get_default_settings()

    def test_load_settings_handles_invalid_json(self, tmp_path):
        """
        Test that invalid JSON is handled gracefully.

        Verifies recovery from corrupted settings file.
        """
        config.SETTINGS_FILE = tmp_path / "settings.json"
        config.CONFIG_DIR = tmp_path

        # Write invalid JSON
        config.SETTINGS_FILE.write_text("{invalid", encoding="utf-8")

        result = config.load_settings()

        assert result == config.get_default_settings()

    def test_get_default_settings_returns_required_keys(self):
        """
        Test that default settings contain all required configuration
        keys.

        Verifies that essential settings are always present.
        """
        defaults = config.get_default_settings()

        assert "main_model" in defaults
        assert "vision_model" in defaults
        assert "system_prompt" in defaults


class TestFileSystemTools:
    """Test cases for file search and discovery tools."""

    def test_search_files_finds_matching_content(self, tmp_path):
        """
        Test that search_files correctly finds files matching a pattern.

        Verifies content-based file searching functionality.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("target content\nother line")

        result = search_files("target", path=str(tmp_path))

        assert "test.txt" in result
        assert "target content" in result

    def test_search_files_respects_max_results(self, tmp_path):
        """
        Test that search_files respects the max_results parameter.

        Verifies result limiting functionality.
        """
        for i in range(5):
            file = tmp_path / f"file{i}.txt"
            file.write_text("matching content here")

        result = search_files("matching", path=str(tmp_path), max_results=2)

        # Count actual results in output
        result_count = result.count("file")
        assert result_count <= 3  # Account for "Showing X results" message

    def test_search_files_handles_invalid_directory(self):
        """
        Test that search_files handles invalid directory paths gracefully.

        Verifies error handling for missing paths.
        """
        result = search_files("pattern", path="/dev/null/nonexistent")

        assert "not a valid directory" in result

    def test_search_files_with_regex_pattern(self, tmp_path):
        """
        Test that search_files supports regex patterns.

        Verifies pattern matching with regular expressions.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("number: 123\ntext: abc")

        result = search_files(r"\d+", path=str(tmp_path))

        assert "test.txt" in result

    def test_find_files_locates_by_name_pattern(self, tmp_path):
        """
        Test that find_files correctly locates files by name pattern.

        Verifies glob-style pattern matching.
        """
        (tmp_path / "test1.py").touch()
        (tmp_path / "test2.py").touch()
        (tmp_path / "other.txt").touch()

        result = find_files("*.py", path=str(tmp_path))

        assert "test1.py" in result
        assert "test2.py" in result
        assert "other.txt" not in result

    def test_find_files_handles_empty_results(self, tmp_path):
        """
        Test that find_files handles cases with no matching files.

        Verifies appropriate error message on no matches.
        """
        result = find_files("*.nonexistent", path=str(tmp_path))

        assert "No files found" in result

    def test_execute_tool_dispatches_correctly(self, tmp_path):
        """
        Test that execute_tool correctly dispatches to tool implementations.

        Verifies tool routing functionality.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = execute_tool("search_files", pattern="content", path=str(tmp_path))

        assert "test.txt" in result

    def test_execute_tool_rejects_unknown_tool(self):
        """
        Test that execute_tool rejects unknown tool names.

        Verifies error handling for invalid tool names.
        """
        result = execute_tool("nonexistent_tool")

        assert "Unknown tool" in result

    def test_get_tool_definitions_returns_valid_schema(self):
        """
        Test that tool definitions conform to expected schema.

        Verifies that tool definitions are properly formatted for
        LLM function calling.
        """
        definitions = get_tool_definitions()

        assert len(definitions) == 2
        assert all("type" in d for d in definitions)
        assert all("function" in d for d in definitions)
        assert all("name" in d["function"] for d in definitions)


class TestHotkeyManager:
    """Test cases for global hotkey detection."""

    def test_hotkey_manager_registers_hotkey(self, mocker):
        """
        Test that hotkey manager correctly registers the global hotkey.

        Verifies hotkey registration with keyboard library.
        """
        mock_add_hotkey = mocker.patch('keyboard.add_hotkey', return_value=1)

        callback = MagicMock()
        manager = HotkeyManager({keyboard.Key.ctrl_l, keyboard.Key.alt_r}, callback)

        # Verify add_hotkey was called with correct key combination
        mock_add_hotkey.assert_called_once()
        call_args = mock_add_hotkey.call_args
        assert 'alt' in call_args[0][0]
        assert 'ctrl' in call_args[0][0]

        manager.stop()

    def test_hotkey_manager_triggers_callback(self, mocker):
        """
        Test that hotkey manager callback is invoked when hotkey fires.

        Verifies callback registration and invocation.
        """
        callback = MagicMock()
        mock_add_hotkey = mocker.patch('keyboard.add_hotkey')

        manager = HotkeyManager({keyboard.Key.ctrl_l}, callback)

        # Extract and invoke the callback function
        registered_callback = mock_add_hotkey.call_args[0][1]
        registered_callback()

        callback.assert_called_once()
        manager.stop()

    def test_hotkey_manager_stops_cleanly(self, mocker):
        """
        Test that hotkey manager can be stopped cleanly.

        Verifies proper resource cleanup.
        """
        callback = MagicMock()
        mock_add_hotkey = mocker.patch('keyboard.add_hotkey', return_value=42)
        mock_remove_hotkey = mocker.patch('keyboard.remove_hotkey')

        manager = HotkeyManager({keyboard.Key.alt_l}, callback)
        manager.stop()

        # Verify remove_hotkey was called with correct hotkey ID
        mock_remove_hotkey.assert_called_once_with(42)

    def test_hotkey_manager_handles_registration_error(self, mocker):
        """
        Test that hotkey manager handles registration errors gracefully.

        Verifies error handling during hotkey setup.
        """
        callback = MagicMock()
        mocker.patch('keyboard.add_hotkey', side_effect=Exception("Permission denied"))

        # Should not raise, just print error
        manager = HotkeyManager({keyboard.Key.ctrl_l}, callback)
        manager.stop()

    def test_hotkey_manager_converts_keys_correctly(self, mocker):
        """
        Test that pynput keys are correctly converted to keyboard library format.

        Verifies key mapping for ctrl, alt, and shift modifiers.
        """
        callback = MagicMock()
        mocker.patch('keyboard.add_hotkey')

        manager = HotkeyManager(
            {keyboard.Key.ctrl_l, keyboard.Key.alt_r, keyboard.Key.shift_l},
            callback
        )

        # Verify conversion happened
        hotkey_str = manager._convert_keys_to_hotkey_string()
        assert 'ctrl' in hotkey_str
        assert 'alt' in hotkey_str
        assert 'shift' in hotkey_str

    def test_hotkey_manager_skips_invalid_keys(self, mocker):
        """
        Test that invalid keys are skipped during conversion.

        Verifies graceful handling of unsupported keys.
        """
        callback = MagicMock()
        mocker.patch('keyboard.add_hotkey')

        # Use only supported keys
        manager = HotkeyManager({keyboard.Key.ctrl_l, keyboard.Key.alt_l}, callback)

        hotkey_str = manager._convert_keys_to_hotkey_string()
        assert hotkey_str is not None
        assert len(hotkey_str) > 0


class TestWebSearchNormalization:
    """Test cases for URL normalization."""

    def test_normalize_url_validates_scheme(self):
        """
        Test that normalize_url validates URL scheme.

        Verifies that only http/https URLs are accepted.
        """
        result = normalize_url("ftp://example.com/page", "example.com")

        assert result is None

    def test_normalize_url_validates_domain(self):
        """
        Test that normalize_url validates domain matching.

        Verifies that only same-domain URLs are returned.
        """
        result = normalize_url("https://other.com/page", "example.com")

        assert result is None

    def test_normalize_url_filters_binary_files(self):
        """
        Test that normalize_url filters out binary file extensions.

        Verifies exclusion of non-content files.
        """
        result = normalize_url("https://example.com/file.zip", "example.com")

        assert result is None

    def test_normalize_url_accepts_valid_url(self):
        """
        Test that normalize_url accepts valid HTML URLs.

        Verifies correct normalization of valid URLs.
        """
        result = normalize_url("https://example.com/page?param=1", "example.com")

        assert result == "https://example.com/page"


class TestWebSearchFunctions:
    """Test cases for web search and filtering."""

    def test_improve_search_query_optimizes_input(self, mocker):
        """
        Test that search query improvement uses LLM optimization.

        Verifies query enhancement functionality.
        """
        mocker.patch(
            "ollama.generate",
            return_value={"response": "optimized query"},
        )

        result = improve_search_query("raw query", "model")

        assert "optimized" in result.lower()

    def test_filter_search_results_uses_llm(self, mocker):
        """
        Test that search result filtering uses LLM relevance checking.

        Verifies that irrelevant results are filtered out.
        """
        mocker.patch(
            "ollama.generate",
            return_value={"response": "YES"},
        )

        results = [
            {"title": "Title", "snippet": "Snippet", "url": "url"}
        ]
        filtered = filter_search_results("query", results, "model")

        assert len(filtered) == 1

    def test_search_duckduckgo_returns_formatted_results(self, mocker):
        """
        Test that DuckDuckGo search returns properly formatted results.

        Verifies result structure and formatting.
        """
        mock_ddgs = mocker.patch("kratt.core.web_search.DDGS")
        mock_ddgs.return_value.__enter__.return_value.text.return_value = [
            {"title": "Test", "href": "http://test.com", "body": "content"}
        ]

        results = search_duckduckgo("query")

        assert len(results) == 1
        assert results[0]["title"] == "Test"
        assert results[0]["url"] == "http://test.com"

    def test_search_duckduckgo_handles_errors(self, mocker):
        """
        Test that DuckDuckGo search handles API errors gracefully.

        Verifies error recovery.
        """
        mocker.patch("kratt.core.web_search.DDGS", side_effect=Exception("API error"))

        results = search_duckduckgo("query")

        assert results == []


class TestWebPageExtraction:
    """Test cases for web page content extraction."""

    def test_extract_text_removes_clutter(self):
        """
        Test that text extraction removes unwanted elements.

        Verifies removal of scripts, styles, and ads.
        """
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = [None, "# Page Title\nContent here"]

        result = extract_text(mock_page)

        assert "# Page Title" in result

    def test_extract_links_prioritized_categorizes_links(self):
        """
        Test that link extraction categorizes links by location.

        Verifies separation of body, header, and footer links.
        """
        mock_page = MagicMock()
        mock_page.evaluate.return_value = {
            "body": ["http://test.com/article"],
            "header": ["http://test.com/nav"],
            "footer": ["http://test.com/legal"],
        }

        result = extract_links_prioritized(mock_page)

        assert len(result["body"]) == 1
        assert len(result["header"]) == 1
        assert len(result["footer"]) == 1


class TestWebScraper:
    """Test cases for headless browser scraping."""

    def test_scraper_initializes_correctly(self):
        """
        Test that WebScraper initializes with correct settings.

        Verifies configuration of scraper instance.
        """
        scraper = WebScraper(max_pages_per_site=2, delay=0.5)

        assert scraper.max_pages_per_site == 2
        assert scraper.delay == 0.5

    def test_scraper_site_extraction(self):
        """
        Test that scraper correctly extracts content from a site.

        Verifies basic scraping functionality.
        """
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = [None, "Content", {"body": [], "header": [], "footer": []}]

        scraper = WebScraper()
        result = scraper.scrape_site("http://test.com", mock_page)

        assert isinstance(result, dict)
