"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class InfringementDetector:
    def __init__(self):
        # OpenAI configuration only
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_endpoint = 'https://api.openai.com/v1/chat/completions'
        self.openai_model = 'gpt-4o'
        
        self.detection_prompt = """
Analyze the apparel image URL  and return JSON with: detected_brands (array), risk_level, detection_details. Rules:
1. **High Risk** triggers if ANY:
   - Visible logos of: adidas (三叶草/三条纹), Nike (swoosh), Converse (starchevron), ASICS (虎爪纹) 
   - Signature design elements:
     •  visible stripes (2/3/4 parallel bands → numeric value for stripe_count) (adidas)
     • Swoosh shape (Nike)
     • Circular star pattern (Converse)
     • ASICS' Tiger Claw stripes
     • Nike Air sole units
     • Converse toe bumper
2. **Low Risk** only when zero brand markers detected

Detection criteria:
- Logo recognition: Minimum 60% similarity to brand's official mark
- Element matching: Shape/configuration matches brand signature patterns

Example response:
{
  "detected_brands": [
    {
      "brand": "Nike",
      "element_type": "design_element",
      "feature": "swoosh_shape"
    },
    {
      "brand": "adidas",
      "element_type": "logo",
      "confidence": 75%
    }
  ],
  "risk_level": "High Risk",
  "detection_details": "Multiple brand markers detected"
}
"""

    def analyze_with_openai(self, image_url: str) -> Optional[Dict]:
        """Analyze image using OpenAI GPT-4o"""
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.openai_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': self.detection_prompt
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': image_url
                                }
                            }
                        ]
                    }
                ],
                'max_tokens': 1000
            }
            
            response = requests.post(
                self.openai_endpoint,
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                # Extract JSON from the response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return None
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error with OpenAI analysis: {e}")
            return None

    def analyze_image(self, image_url: str) -> Optional[Dict]:
        """Main method to analyze an image for infringement"""
        print(f"Analyzing image: {image_url}")
        
        if not self.openai_api_key:
            print("OpenAI API key not configured")
            return None
            
        return self.analyze_with_openai(image_url)

    def batch_analyze(self, products: List[Dict]) -> List[Dict]:
        """Analyze multiple products in batch"""
        results = []
        
        for product in products:
            analysis = self.analyze_image(product['image_url'])
            if analysis:
                product['infringement_analysis'] = analysis
            else:
                product['infringement_analysis'] = {
                    'detected_brands': [],
                    'risk_level': 'Unknown',
                    'detection_details': 'Analysis failed'
                }
            results.append(product)
            
        return results

if __name__ == '__main__':
    # Example usage
    detector = InfringementDetector()
    
    # Test with a sample image
    test_image = "https://example.com/test-image.jpg"
    result = detector.analyze_image(test_image)
    
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed") 