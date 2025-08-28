"""Version and capability tracking for idea_bot"""

# Version format: MAJOR.MINOR.PATCH
VERSION = "1.2.0"  # Increment version for new image capabilities

# Capabilities - used to track what features are available
CAPABILITIES = {
    "file_handling": {
        "enabled": True,
        "max_size": "20MB",
        "supported_types": ["CSV", "Excel", "PDF", "Image"],
        "features": [
            "File upload and download",
            "Content analysis",
            "Data extraction",
            "Image recognition",
            "Context memory",
            "Business data analysis",
            "Product image analysis",
            "Sales report processing",
            "Customer feedback analysis"
        ]
    },
    "chat": {
        "enabled": True,
        "features": [
            "Context awareness",
            "Memory retention (1 hour)",
            "Multi-turn conversations",
            "File context integration",
            "Image analysis",
            "Multilingual support (Chinese/English)",
            "Business conversation support",
            "Halara-specific knowledge",
            "Professional workplace communication"
        ]
    },
    "business_support": {
        "enabled": True,
        "features": [
            "Product data analysis",
            "Sales performance insights",
            "Customer behavior analysis",
            "Inventory management support",
            "Marketing content analysis",
            "Quality control assistance",
            "Competitive analysis",
            "Market research support",
            "E-commerce optimization",
            "Fashion industry expertise"
        ]
    }
}

def get_version_info():
    """Get a formatted string with version and capability information"""
    return f"idea_bot v{VERSION}"

def get_capabilities():
    """Get a formatted string listing all current capabilities"""
    cap_list = []
    if CAPABILITIES["file_handling"]["enabled"]:
        cap_list.extend([
            f"📄 File handling up to {CAPABILITIES['file_handling']['max_size']}",
            f"📊 Supported formats: {', '.join(CAPABILITIES['file_handling']['supported_types'])}",
            "💾 1-hour context memory",
            "🔍 Advanced file analysis",
            "📈 Business data analysis",
            "🖼️ Product image analysis"
        ])
    if CAPABILITIES["chat"]["enabled"]:
        cap_list.extend([
            "💬 Context-aware conversations",
            "🧠 Integrated file and chat memory",
            "🔄 Multi-turn dialogue support",
            "🌐 Multilingual support (Chinese/English)",
            "🏢 Professional workplace communication"
        ])
    if CAPABILITIES["business_support"]["enabled"]:
        cap_list.extend([
            "📊 Product data analysis",
            "💰 Sales performance insights",
            "👥 Customer behavior analysis",
            "📦 Inventory management support",
            "📢 Marketing content analysis",
            "✅ Quality control assistance",
            "🎯 Competitive analysis",
            "🔍 Market research support",
            "🛒 E-commerce optimization",
            "👗 Fashion industry expertise"
        ])
    return cap_list 