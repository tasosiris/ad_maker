# AI-Powered Video Generation Pipeline

This document explains the entire pipeline of the AI-powered video generation system, from the initial idea to the final rendered video. The process is designed to be interactive, allowing for user feedback at crucial stages.

## High-Level Overview

The pipeline can be broken down into the following major steps:

1.  **Idea Generation**: Based on a user-selected category, several ad ideas are generated.
2.  **Idea Selection**: The user selects the most promising idea.
3.  **Product Search**: The system finds real products related to the selected idea.
4.  **Product Selection**: The user selects a product to be featured in the ad.
5.  **Script Generation**: A script (either long-form or short-form) is generated for the ad.
6.  **Feedback and Approval**: The user reviews the script and can approve it for production or request changes.
7.  **Video Composition**: Once a script is approved, the system generates the final video by combining text-to-speech audio with visual assets.

Below is a detailed breakdown of each step.

---

## Step-by-Step Breakdown

### 1. Select Product Category

*   **Description**: The pipeline starts with the user selecting a category for the product they want to advertise. This helps focus the creative process.
*   **Script(s) Involved**: `main.py`, `src/agents/idea_selector.py`
*   **Input**: User's choice from a predefined list of categories (e.g., "Skincare", "Kitchen Gadgets", "Pet Accessories").
*   **Output**: The selected category name.
*   **Example**: The user is presented with a list and selects "Kitchen Gadgets".

### 2. Generate Ad Ideas

*   **Description**: The system generates a set of creative and engaging ad ideas based on the selected category.
*   **Script(s) Involved**: `main.py`, `src/agents/idea_generator.py`
*   **Input**: The product category (e.g., "Kitchen Gadgets").
*   **Output**: A list of short, compelling ad concepts.
*   **Example Output**:
    1.  "A series of quick cuts showing a revolutionary new blender making smoothies, soups, and nut butters effortlessly."
    2.  "A funny ad showing someone struggling with old, dull knives, then discovering a self-sharpening knife block."
    3.  "A heartwarming story of a family cooking together using a new smart oven."

### 3. Select an Idea

*   **Description**: The user reviews the generated ideas and selects the one they like the most.
*   **Script(s) Involved**: `main.py`
*   **Input**: The list of generated ad ideas.
*   **Output**: The single, chosen ad idea.
*   **Example**: The user chooses idea #2: "A funny ad showing someone struggling with old, dull knives, then discovering a self-sharpening knife block."

### 4. Find Real Products

*   **Description**: To make the ad more concrete, the system searches for real products that match the selected idea and category. The system performs a **Google search** using a query like "top affiliate products for [idea] in [category]" and extracts product names and URLs from the search results.
*   **Script(s) Involved**: `main.py`, `src/agents/product_finder.py`
*   **Input**: The selected ad idea and category.
*   **Output**: A list of real products with their names and URLs scraped from Google search results.
*   **How it works**: 
    1. Creates a search query: `"top affiliate products for [idea] in [category]"`
    2. Sends a request to Google Search with proper headers to avoid blocking
    3. Parses the HTML response using BeautifulSoup
    4. Extracts product titles from `<h3>` tags in search results
    5. Filters out irrelevant results and gets associated URLs
*   **Example Search Query**: `"top affiliate products for A funny ad showing someone struggling with old, dull knives, then discovering a self-sharpening knife block in Kitchen Gadgets"`
*   **Example Output**:
    1.  `{ 'name': 'Calphalon Classic Self-Sharpening 15-piece Knife Block Set', 'url': 'https://...' }`
    2.  `{ 'name': 'Henckels Graphite 14-pc. Self-Sharpening Block Set', 'url': 'https://...' }`

### 5. Select a Product

*   **Description**: The user can select a specific product to be featured in the ad. This step is optional.
*   **Script(s) Involved**: `main.py`
*   **Input**: The list of found products.
*   **Output**: The chosen product, or a decision to proceed with a generic script.
*   **Example**: User selects the "Calphalon Classic" knife set.

### 6. Generate Script

*   **Description**: A detailed script is generated based on the selected idea and product. The user can choose between a `long_form` (e.g., for YouTube) or `short_form` (e.g., for TikTok/Shorts) script. The script includes scenes, narration, and visual cues.
*   **Script(s) Involved**: `main.py`, `src/agents/script_generator.py`, `src/templates/`
*   **Input**: The selected ad idea, chosen product (optional), and desired script format (`long` or `short`).
*   **Output**: A complete script object.
*   **Example Snippet (Short Form)**:
    ```json
    {
      "title": "The Last Knife You'll Ever Need",
      "scenes": [
        {
          "scene_number": 1,
          "narration": "Tired of dull knives that can't even cut a tomato?",
          "visual_cue": "Close-up shot of a knife struggling to slice a tomato, squishing it instead."
        },
        {
          "scene_number": 2,
          "narration": "Introducing the Calphalon Self-Sharpening Knife Set. Every time you pull out a knife, it's perfectly sharp.",
          "visual_cue": "Show the Calphalon knife block. A hand smoothly pulls out a chef's knife."
        }
      ]
    }
    ```

### 7. Review & Approve Script

*   **Description**: The user is shown a summary of the generated script and can provide feedback. They can approve the script for video production, ask for modifications, or reject it.
*   **Script(s) Involved**: `main.py`, `src/controllers/feedback.py`
*   **Input**: The generated script. User's feedback (approve/reject).
*   **Output**: An approved script, ready for video composition.
*   **Example**: The user sees the script summary and types "approve".

### 8. Compose Video

*   **Description**: This is the final and most complex stage. Once a script is approved, the system automatically creates the video.
*   **Script(s) Involved**: `src/agents/video_composer.py`
*   **This stage involves several sub-steps**:
    1.  **Text-to-Speech (TTS)**: The narration from the script is converted into a realistic voiceover.
        *   **Script**: `src/tts/voice.py`
        *   **Input**: The narration text for each scene.
        *   **Output**: Audio files (`.mp3`) for each line of narration.
    2.  **Fetch Visual Assets**: The system searches for and downloads stock videos or images that match the `visual_cue` for each scene.
        *   **Script**: `src/assets/fetcher.py`
        *   **Input**: The `visual_cue` text (e.g., "A hand smoothly pulls out a chef's knife").
        *   **Output**: Video clips (`.mp4`) or images for each scene.
    3.  **Video Editing**: The downloaded visual assets are edited together. The audio voiceover is synchronized with the corresponding video clips, and background music or subtitles can be added.
        *   **Script**: `src/editing/ffmpeg_editor.py`
        *   **Input**: The audio files and visual asset files.
        *   **Output**: The final, composed video ad (`.mp4`).
*   **Final Output**: A complete video file saved in the `output/` directory, along with comprehensive metadata files.

---

## Output Files

When a video is successfully generated, the system creates multiple files in the output directory:

### File Structure
```
output/
├── [Category]/
│   └── [Idea]/
│       └── [script_type]/
│           ├── script_[ID]_[timestamp].mp4     # The final video
│           ├── script_[ID]_[timestamp].json    # Comprehensive metadata
│           └── script_[ID]_[timestamp]_script.txt  # Human-readable script
```

### 1. Video File (`.mp4`)
The main video output with synchronized audio and visuals.

### 2. Metadata File (`.json`)
Contains comprehensive information about the video:
```json
{
  "video_info": {
    "title": "Smart Kitchen Knife Block Review",
    "description": "Tired of dull knives that can't even cut a tomato?...",
    "tags": ["kitchen", "gadgets", "knife", "review", "affiliate"],
    "category": "Kitchen_Gadgets",
    "script_type": "short_form"
  },
  "script_content": {
    "full_script": "Complete script text here...",
    "script_id": 123,
    "job_id": 45
  },
  "product_info": {
    "name": "Calphalon Classic Self-Sharpening 15-piece Knife Block Set",
    "url": "https://amazon.com/product-link",
    "affiliate_commission": "3-8%"
  },
  "affiliate_links": {
    "Calphalon Classic Self-Sharpening 15-piece Knife Block Set": "https://amazon.com/product-link"
  },
  "generation_info": {
    "idea": "A funny ad showing someone struggling with old, dull knives...",
    "category": "Kitchen_Gadgets",
    "created_at": "2024-01-15 10:30:00",
    "script_status": "approved"
  }
}
```

### 3. Script Text File (`.txt`)
A human-readable version of all the information:
```
TITLE: Smart Kitchen Knife Block Review
CATEGORY: Kitchen_Gadgets
IDEA: A funny ad showing someone struggling with old, dull knives...
PRODUCT: Calphalon Classic Self-Sharpening 15-piece Knife Block Set
COMMISSION: 3-8%
LINK: https://amazon.com/product-link

==================================================
SCRIPT CONTENT:
==================================================

[Full script content here...]
```

---

## Affiliate Information

The system automatically extracts and stores affiliate commission information:

- **Commission Rates**: Estimated based on product type and detected from search results
- **Product Links**: Direct URLs to the products found during the search process
- **Default Rates**: 
  - Amazon products: 1-10%
  - Kitchen/Home products: 3-8%
  - Electronics: 2-6%
  - General products: 3-7%

This information is saved with every video, making it easy to:
- Track potential earnings
- Update affiliate links
- Upload to platforms with proper attribution
- Maintain records for tax purposes 