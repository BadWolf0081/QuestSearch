#!/bin/bash
# filepath: c:\Users\robbi\OneDrive\Documents\GitHub\QuestSearch\extract_pokemon_icons.sh

INPUT="data/api.json"
OUTPUT="pokemon_icons.json"

awk '
    match($0, /<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<img src="(pokemon\/[^"]+)"/, arr) {
        name=arr[1]
        form=arr[3]
        costume=arr[4]
        img=arr[5]
        # Remove leading/trailing whitespace
        gsub(/^ +| +$/, "", name)
        gsub(/^ +| +$/, "", form)
        gsub(/^ +| +$/, "", costume)
        print "{\"name\": \"" name "\", \"form\": \"" form "\", \"costume\": \"" costume "\", \"img\": \"" img "\"}"
    }
' "$INPUT" | jq -s '.' > "$OUTPUT"

echo "Output written to $OUTPUT"