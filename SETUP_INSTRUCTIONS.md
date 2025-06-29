# Setup Instructions for Enhanced Video Generation

## New Features Added

Your AI video generation system now includes comprehensive affiliate tracking and metadata generation. Here's what's new:

### 🆕 Enhanced Product Information
- **Affiliate Commission Tracking**: Automatically detects and estimates commission rates
- **Product URL Storage**: Saves direct links to featured products
- **Comprehensive Metadata**: Generates detailed JSON and text files alongside each video

### 📁 Enhanced Output Files
Each generated video now comes with:
- `video.mp4` - The main video file
- `video.json` - Comprehensive metadata (perfect for automation)
- `video_script.txt` - Human-readable script and product info

## Setup Steps

### 1. Update Your Database
If you have an existing database, run the migration script:

```bash
python migrate_product_fields.py
```

This adds the new product fields to your existing jobs without losing data.

### 2. Fresh Database Setup
If you're starting fresh:

```bash
python main.py setup-database
```

### 3. Run the Enhanced Pipeline
```bash
python main.py run-full-pipeline
```

The system will now:
1. Find real products with affiliate information
2. Store product details in the database
3. Generate videos with comprehensive metadata
4. Save affiliate links and commission rates

## What You Get

### Example Output Structure
```
output/Kitchen_Gadgets/Smart_Knife_Block/short_form/
├── script_123_1704567890.mp4        # Your video
├── script_123_1704567890.json       # Metadata for automation
└── script_123_1704567890_script.txt # Human-readable info
```

### Metadata Includes
- **Video Information**: Title, description, tags optimized for platforms
- **Complete Script**: Full text content for reference
- **Product Details**: Name, URL, estimated commission rates
- **Affiliate Links**: Ready-to-use links for monetization
- **Generation Info**: Timestamps, categories, and tracking data

## Benefits

### 🎯 **For Content Creators**
- Automatic affiliate link organization
- Commission rate tracking for revenue planning
- Platform-ready metadata (YouTube, TikTok, etc.)
- Easy script reference for video descriptions

### 🤖 **For Automation**
- JSON metadata perfect for batch processing
- Structured data for analytics and reporting
- API-ready format for integration with other tools

### 💰 **For Monetization**
- Automatic commission rate estimation
- Organized affiliate links
- Revenue tracking preparation
- Tax record maintenance

## Advanced Usage

### Custom Commission Rates
The system intelligently estimates commission rates based on:
- Product category (Kitchen: 3-8%, Electronics: 2-6%, etc.)
- Detected affiliate programs (Amazon: 1-10%)
- Search result analysis

### Batch Processing
All metadata is structured for easy batch processing:
```python
import json
with open('script_123_1704567890.json', 'r') as f:
    metadata = json.load(f)
    product_url = metadata['product_info']['url']
    commission = metadata['product_info']['affiliate_commission']
```

## Troubleshooting

### Migration Issues
If the migration script fails:
1. Check your database connection in `config.yaml`
2. Ensure you have write permissions
3. For SQLite: Check the database file exists
4. For PostgreSQL: Verify connection string

### Missing Product Information
If products aren't being found:
1. Check your internet connection
2. Try different search terms in your ideas
3. The system will still work with generic scripts if no products are found

## Next Steps

1. **Run the migration** (if you have existing data)
2. **Test the pipeline** with a simple category
3. **Check the output files** to see the new metadata
4. **Integrate with your workflow** using the JSON metadata

Your video generation system is now ready for serious affiliate marketing! 🚀 