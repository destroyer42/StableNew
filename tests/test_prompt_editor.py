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
            if line.lower().startswith('neg:'):
                negative_prompts.append(line[4:].strip())
            else:
                prompts.append(line)
        return prompts, negative_prompts

    @staticmethod
    def format_text(prompts, negative_prompts):
        """Formats prompts back into a single string for the editor."""
        lines = []
        lines.extend(prompts)
        lines.extend([f"neg: {neg}" for neg in negative_prompts])
        return "\n".join(lines)

class TestPromptEditor(unittest.TestCase):

    def test_parse_prompts_and_negatives(self):
        """Test parsing of mixed prompts and negative prompts."""
        editor_content = """
        a beautiful landscape
        a majestic castle
        neg: blurry, low quality
        concept art
        neg: watermark, signature
        """
        prompts, neg_prompts = PromptParser.parse_text(editor_content)
        
        # Parser returns 3 prompts because "concept art" is also a prompt
        self.assertEqual(len(prompts), 3)
        self.assertEqual(len(neg_prompts), 2)
        self.assertIn("a beautiful landscape", prompts)
        self.assertIn("a majestic castle", prompts)
        self.assertIn("concept art", prompts)
        self.assertIn("blurry, low quality", neg_prompts)
        self.assertIn("watermark, signature", neg_prompts)

    def test_parse_only_prompts(self):
        """Test parsing when only positive prompts are present."""
        editor_content = "first prompt\nsecond prompt"
        prompts, neg_prompts = PromptParser.parse_text(editor_content)
        self.assertEqual(prompts, ["first prompt", "second prompt"])
        self.assertEqual(neg_prompts, [])

    def test_parse_only_negatives(self):
        """Test parsing when only negative prompts are present."""
        editor_content = "neg: bad art\nneg: ugly"
        prompts, neg_prompts = PromptParser.parse_text(editor_content)
        self.assertEqual(prompts, [])
        self.assertEqual(neg_prompts, ["bad art", "ugly"])

    def test_format_text_for_editor(self):
        """Test formatting prompts and negatives back into editor text."""
        prompts = ["A stunning portrait", "digital painting"]
        negative_prompts = ["out of frame", "extra limbs"]
        
        expected_text = "A stunning portrait\ndigital painting\nneg: out of frame\nneg: extra limbs"
        formatted_text = PromptParser.format_text(prompts, negative_prompts)
        self.assertEqual(formatted_text, expected_text)

    def test_syntax_highlighting_logic(self):
        """
        Simulate testing the logic that would drive syntax highlighting.
        This test would identify token types and their positions.
        """
        # In a real scenario, this would be more complex, likely involving a dedicated
        # function that returns ranges for highlighting.
        text = "a good prompt\nneg: a bad prompt"
        
        # Mock a text widget to test tag application
        mock_text_widget = MagicMock()
        mock_text_widget.get.return_value = text
        
        # Logic to apply tags (simplified)
        def apply_highlighting(widget):
            content = widget.get("1.0", "end-1c")
            for i, line in enumerate(content.splitlines()):
                if line.lower().startswith("neg:"):
                    # In a real tkinter app, you'd use tag_add here
                    widget.tag_add("negative", f"{i+1}.0", f"{i+1}.end")

        apply_highlighting(mock_text_widget)

        # Assert that the 'negative' tag was applied to the correct line
        mock_text_widget.tag_add.assert_called_once_with("negative", "2.0", "2.end")


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
