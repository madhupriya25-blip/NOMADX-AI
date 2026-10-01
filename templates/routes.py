# Add to your Flask routes.py

@app.route('/api/emergency/suggest')
def emergency_suggest():
    """Get search suggestions for emergency numbers"""
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    suggestions = set()
    for entry in EMERGENCY_DATABASE:  # Use the database from above
        country = entry.get('country', '').lower()
        state = entry.get('state', '').lower()
        city = entry.get('city', '').lower()
        
        if query in country:
            suggestions.add(entry['country'])
        if query in state:
            suggestions.add(f"{entry['state']} ({entry['country']})")
        if query in city:
            suggestions.add(f"{entry['city']} ({entry['country']})")
    
    return jsonify({'suggestions': list(suggestions)[:10]})


@app.route('/api/emergency/search')
def emergency_search():
    """Search emergency numbers worldwide"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all').strip()
    
    if not query:
        return jsonify({'error': 'Please enter a search term', 'results': []})
    
    query_lower = query.lower()
    results = []
    
    for entry in EMERGENCY_DATABASE:
        matches = False
        
        # Search in country, state, city
        if (query_lower in entry.get('country', '').lower() or
            query_lower in entry.get('state', '').lower() or
            query_lower in entry.get('city', '').lower()):
            matches = True
        
        # Search in category values
        if not matches:
            category_map = {
                'police': entry.get('police', ''),
                'ambulance': entry.get('ambulance', ''),
                'fire': entry.get('fire', ''),
                'women': entry.get('women', ''),
                'child': entry.get('child', ''),
                'tourist': entry.get('tourist', ''),
                'disaster': entry.get('disaster', ''),
                'medical': entry.get('medical', ''),
                'embassy': entry.get('embassy', ''),
                'hospital': entry.get('hospital', '')
            }
            for cat, value in category_map.items():
                if value and query_lower in value.lower():
                    matches = True
                    break
                if query_lower in cat:
                    matches = True
                    break
        
        if not matches:
            continue
        
        # Apply category filter
        if category != 'all':
            category_map = {
                'police': entry.get('police', ''),
                'ambulance': entry.get('ambulance', ''),
                'fire': entry.get('fire', ''),
                'women': entry.get('women', ''),
                'child': entry.get('child', ''),
                'medical': entry.get('medical', ''),
                'disaster': entry.get('disaster', ''),
                'tourist': entry.get('tourist', ''),
                'embassy': entry.get('embassy', ''),
                'hospital': entry.get('hospital', '')
            }
            if category not in category_map or not category_map[category]:
                continue
        
        # Determine which number to show
        number = None
        icon = '📞'
        display_category = 'Emergency'
        
        if category != 'all':
            number = category_map.get(category)
            display_category = category.capitalize()
            icon_map = {
                'police': '🚓', 'ambulance': '🚑', 'fire': '🚒',
                'women': '👩', 'child': '👶', 'medical': '🏥',
                'disaster': '🚨', 'tourist': '🌍', 'embassy': '🏛',
                'hospital': '🏥'
            }
            icon = icon_map.get(category, '📞')
        else:
            # Show first available number
            for cat in ['police', 'ambulance', 'fire', 'women', 'child', 'medical', 'tourist', 'disaster']:
                if entry.get(cat):
                    number = entry[cat]
                    display_category = cat.capitalize()
                    icon_map = {
                        'police': '🚓', 'ambulance': '🚑', 'fire': '🚒',
                        'women': '👩', 'child': '👶', 'medical': '🏥',
                        'disaster': '🚨', 'tourist': '🌍', 'embassy': '🏛'
                    }
                    icon = icon_map.get(cat, '📞')
                    break
        
        if not number:
            continue
        
        results.append({
            'country': entry.get('country', 'Unknown'),
            'state': entry.get('state', 'All'),
            'city': entry.get('city', ''),
            'number': number,
            'category': display_category,
            'icon': icon,
            'hospital': entry.get('hospital', ''),
            'embassy': entry.get('embassy', '')
        })
    
    return jsonify({'results': results, 'count': len(results)})