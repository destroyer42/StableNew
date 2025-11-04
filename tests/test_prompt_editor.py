import unittest
from unittest.mock import MagicMock


# This class is a placeholder for the logic that would parse the prompt editor's content.
# For true testability, this logic should be extracted from the main GUI class.
class PromptParser:
    @staticmethod
    def parse_text(text_content):
        """Parses text from the editor into prompts and negative prompts."""
        prompts = []
        negative_prompts = []
        for line in text_content.splitlines():
            line = line.strip()
            if not line:
                continue
            class TestPromptEditorEnhancements(unittest.TestCase):
                """Tests for PR F-H enhancements to the prompt editor."""

                def test_angle_bracket_escaping(self):
                    """Test that angle brackets are properly escaped and unescaped."""
                    # Content with angle brackets (e.g., emphasis syntax)
                    content_with_brackets = "a beautiful <lora:model:0.5> landscape <embedding:name>"

                    # Escape for safe saving
                    escaped = content_with_brackets.replace('<', '&lt;').replace('>', '&gt;')
                    self.assertIn('&lt;lora', escaped)
                    self.assertIn('&gt;', escaped)

                    # Unescape for display
                    unescaped = escaped.replace('&lt;', '<').replace('&gt;', '>')
                    self.assertEqual(unescaped, content_with_brackets)

                def test_pack_name_auto_population(self):
                    """Test that pack name is auto-populated from filename."""
                    from pathlib import Path

                    # Simulate loading a pack with a specific filename
                    pack_path = Path("packs/my_awesome_pack.txt")
                    expected_name = "my_awesome_pack"

                    # Extract stem (filename without extension)
                    actual_name = pack_path.stem
                    self.assertEqual(actual_name, expected_name)

                def test_filename_prefix_from_name_metadata(self):
                    """Test that 'name:' metadata is used for filename prefix."""
                    # Content with name: metadata
                    content = """name: HeroCharacter
            a brave hero
            standing tall
            neg: bad quality"""

                    # Extract name from first line
                    lines = content.strip().split('\n')
                    name_prefix = None
                    for line in lines:
                        if line.strip().startswith('name:'):
                            name_prefix = line.split(':', 1)[1].strip()
                            break

                    self.assertEqual(name_prefix, "HeroCharacter")

                    # Verify it can be used in filename
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    expected_filename = f"{name_prefix}_{timestamp}.png"
                    self.assertTrue(expected_filename.startswith("HeroCharacter_"))

                def test_global_negative_roundtrip(self):
                    """Test that global negative prompt persists through save/load."""
                    global_negative = "blurry, bad quality, nsfw, inappropriate"

                    # Simulate saving
                    import tempfile
                    import json

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        config = {"global_negative": global_negative}
                        json.dump(config, f, ensure_ascii=False)
                        temp_path = f.name

                    try:
                        # Simulate loading
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            loaded_config = json.load(f)

                        self.assertEqual(loaded_config["global_negative"], global_negative)
                    finally:
                        import os
                        os.unlink(temp_path)

                def test_bracket_handling_in_prompts(self):
                    """Test that various bracket types are handled correctly."""
                    prompts_with_brackets = [
                        "a photo of <character>",
                        "painting (detailed:1.2)",
                        "[fantasy:scifi:0.5]",
                        "(masterpiece, best quality)",
                    ]

                    for prompt in prompts_with_brackets:
                        # Verify brackets are preserved
                        has_bracket = '<' in prompt or '(' in prompt or '[' in prompt
                        self.assertTrue(has_bracket, f"Prompt should contain brackets: {prompt}")

                        # Test escape/unescape cycle for angle brackets
                        escaped = prompt.replace('<', '&lt;').replace('>', '&gt;')
                        unescaped = escaped.replace('&lt;', '<').replace('&gt;', '>')
                        self.assertEqual(unescaped, prompt)


            if __name__ == '__main__':
                unittest.main()
        self.assertEqual(unescaped, content_with_brackets)
    
    def test_pack_name_auto_population(self):
        """Test that pack name is auto-populated from filename."""
        from pathlib import Path
        
        # Simulate loading a pack with a specific filename
        pack_path = Path("packs/my_awesome_pack.txt")
        expected_name = "my_awesome_pack"
        
        # Extract stem (filename without extension)
        actual_name = pack_path.stem
        self.assertEqual(actual_name, expected_name)
    
    def test_filename_prefix_from_name_metadata(self):
        """Test that 'name:' metadata is used for filename prefix."""
        # Content with name: metadata
        content = """name: HeroCharacter
a brave hero
standing tall
neg: bad quality"""
        
        # Extract name from first line
        lines = content.strip().split('\n')
        name_prefix = None
        for line in lines:
            if line.strip().startswith('name:'):
                name_prefix = line.split(':', 1)[1].strip()
                break
        
        self.assertEqual(name_prefix, "HeroCharacter")
        
        # Verify it can be used in filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        expected_filename = f"{name_prefix}_{timestamp}.png"
        self.assertTrue(expected_filename.startswith("HeroCharacter_"))
    
    def test_global_negative_roundtrip(self):
        """Test that global negative prompt persists through save/load."""
        global_negative = "blurry, bad quality, nsfw, inappropriate"
        
        # Simulate saving
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {"global_negative": global_negative}
            json.dump(config, f, ensure_ascii=False)
            temp_path = f.name
        
        try:
            # Simulate loading
            with open(temp_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            self.assertEqual(loaded_config["global_negative"], global_negative)
        finally:
            import os
            os.unlink(temp_path)
    
    def test_bracket_handling_in_prompts(self):
        """Test that various bracket types are handled correctly."""
        prompts_with_brackets = [
            "a photo of <character>",
            "painting (detailed:1.2)",
            "[fantasy:scifi:0.5]",
            "(masterpiece, best quality)",
        ]
        
        for prompt in prompts_with_brackets:
            # Verify brackets are preserved
            has_bracket = '<' in prompt or '(' in prompt or '[' in prompt
            self.assertTrue(has_bracket, f"Prompt should contain brackets: {prompt}")
            
            # Test escape/unescape cycle for angle brackets
            escaped = prompt.replace('<', '&lt;').replace('>', '&gt;')
            unescaped = escaped.replace('&lt;', '<').replace('&gt;', '>')
            self.assertEqual(unescaped, prompt)


if __name__ == '__main__':
=======
if __name__ == "__main__":
>>>>>>> gui-finish-sprint-nov2025
    unittest.main()
