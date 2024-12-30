# import torch
# import torch.nn as nn
# import torchvision.models as models
# import torchvision.transforms as transforms
# from PIL import Image
# import numpy as np
# import io
# import base64
# from transformers import CLIPProcessor, CLIPModel

# # class UIElementFinder:
# #     def __init__(self):
# #         """Initialize the models for visual feature extraction and text embedding"""
# #         # Load CLIP model for semantic matching
# #         self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
# #         self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
# #         # Move model to GPU if available
# #         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# #         self.clip_model = self.clip_model.to(self.device)

# #     def extract_patches(self, image, kernel_size=10, stride=5):
# #         """
# #         Extract overlapping patches from the image using sliding windows.
        
# #         Args:
# #             image: PIL Image
# #             kernel_size: Size of the sliding window
# #             stride: Step size for sliding window
        
# #         Returns:
# #             list: List of (patch, coordinates) tuples
# #         """
# #         # Convert image to numpy array if it's not already
# #         if isinstance(image, Image.Image):
# #             image_array = np.array(image)
# #         else:
# #             image_array = image
            
# #         height, width = image_array.shape[:2]
# #         patches = []
        
# #         for y in range(0, height - kernel_size, stride):
# #             for x in range(0, width - kernel_size, stride):
# #                 print("processing patch ", x, y)
# #                 # Extract patch
# #                 patch = image_array[y:y + kernel_size, x:x + kernel_size]
# #                 # Convert patch to PIL Image
# #                 patch_image = Image.fromarray(patch)
# #                 # Store patch with its coordinates
# #                 patches.append((patch_image, (x + kernel_size//2, y + kernel_size//2)))
                
# #         return patches

# #     def compute_semantic_similarity(self, image_patches, target_text):
# #         """
# #         Compute semantic similarity between image patches and target text using CLIP.
        
# #         Args:
# #             image_patches: List of (patch, coordinates) tuples
# #             target_text: Text to match against
            
# #         Returns:
# #             tuple: Coordinates of best matching patch and similarity score
# #         """
# #         patches, coordinates = zip(*image_patches)
        
# #         # Prepare text input
# #         text_inputs = self.clip_processor(
# #             text=[target_text],
# #             return_tensors="pt",
# #             padding=True
# #         ).to(self.device)
        
# #         # Get text features
# #         with torch.no_grad():
# #             text_features = self.clip_model.get_text_features(**text_inputs)
        
# #         best_similarity = -1
# #         best_coordinates = None
        
# #         # Process patches in batches to avoid memory issues
# #         batch_size = 32
# #         for i in range(0, len(patches), batch_size):
# #             print("processing batch ", i, " of ", len(patches) // batch_size)
# #             batch_patches = patches[i:i + batch_size]
# #             batch_coords = coordinates[i:i + batch_size]
            
# #             # Prepare image inputs
# #             image_inputs = self.clip_processor(
# #                 images=batch_patches,
# #                 return_tensors="pt",
# #                 padding=True
# #             ).to(self.device)
            
# #             # Get image features
# #             with torch.no_grad():
# #                 image_features = self.clip_model.get_image_features(**image_inputs)
            
# #             # Compute similarities
# #             similarities = torch.nn.functional.cosine_similarity(
# #                 image_features.unsqueeze(1),
# #                 text_features.unsqueeze(0),
# #                 dim=-1
# #             )
            
# #             # Find best match in batch
# #             batch_best_idx = torch.argmax(similarities).item()
# #             batch_best_similarity = similarities[batch_best_idx].item()
            
# #             if batch_best_similarity > best_similarity:
# #                 best_similarity = batch_best_similarity
# #                 best_coordinates = batch_coords[batch_best_idx]
        
# #         return best_coordinates, best_similarity

# # def find_element_in_screenshot(screenshot, element_text):
# #     """
# #     Find an element in a screenshot using semantic matching with CLIP.
    
# #     Args:
# #         screenshot: PIL Image or base64 encoded image string
# #         element_text: Text of the element to find
        
# #     Returns:
# #         tuple: (x, y) coordinates of best matching region, or None if no good match found
# #         float: Confidence score of the match
# #     """
# #     # Convert base64 to PIL Image if needed
# #     if isinstance(screenshot, str) and screenshot.startswith('data:image'):
# #         base64_data = screenshot.split(',')[1]
# #         image_data = base64.b64decode(base64_data)
# #         screenshot = Image.open(io.BytesIO(image_data))
    
# #     # Initialize finder
# #     finder = UIElementFinder()
    
# #     # Extract patches
# #     patches = finder.extract_patches(screenshot, kernel_size=10, stride=5)
    
# #     # Find best matching patch
# #     coordinates, similarity = finder.compute_semantic_similarity(patches, element_text)
    
# #     # Return None if similarity is too low
# #     if similarity < 0.2:  # Adjust threshold as needed
# #         return None, similarity
        
# #     return coordinates, similarity

# # # Example usage
# # if __name__ == "__main__":
# #     element_to_find = "Bold button"
# #     # Assuming screenshot is a PIL Image
# #     screenshot = Image.open("browser.png")
# #     print("screenshot loaded")
# #     coordinates, confidence = find_element_in_screenshot(screenshot, element_to_find)
# #     print(f"Element '{element_to_find}' found at coordinates: {coordinates} with confidence: {confidence}")


# screenshot = Image.open("browser.png")
# text = "Bold button"


# clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
# clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# with torch.no_grad():
#     inputs = clip_processor(text=[text], images=[screenshot], return_tensors="pt", padding=True)
#     outputs = clip_model(**inputs)
#     image_features = outputs.image_embeds
#     text_features = outputs.text_embeds
#     similarity = torch.nn.functional.cosine_similarity(image_features, text_features)
#     print(f"Semantic similarity: {similarity.item()}")
# # 


# import requests

# import torch
# from PIL import Image, ImageDraw
# from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

# model_id = "IDEA-Research/grounding-dino-tiny"
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# processor = AutoProcessor.from_pretrained(model_id)
# model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

# image = Image.open("browser.png").convert('RGB')
# draw = ImageDraw.Draw(image)

# text = "a bold button"

# inputs = processor(images=image, text=text, return_tensors="pt").to(device)
# with torch.no_grad():
#     outputs = model(**inputs)

# results = processor.post_process_grounded_object_detection(
#     outputs,
#     inputs.input_ids,
#     box_threshold=0.1,
#     text_threshold=0.1,
#     target_sizes=[image.size[::-1]]
# )

# print(results)
# print(results[0]["boxes"].tolist())

# for result in results:
#     boxes = result['boxes']
#     scores = result['scores']
#     for box, score in zip(boxes, scores):
#         box = box.tolist()
#         draw.rectangle(box, outline="red", width=2)
#         draw.text((box[0], box[1] - 10), f"{score:.2f}", fill="red")

# image.save("edited.png")