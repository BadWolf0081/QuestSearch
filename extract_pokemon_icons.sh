#!/bin/bash

INPUT="data/api.json"
OUTPUT="pokemon_icons.json"

awk '
    # For each table row, extract the relevant fields and the img src
    match($0, /<tr>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<td>([^<]*)<\/td>.*<img src="(pokemon\/[^"]+)"/, arr) {
        name=arr[1]
        form=arr[3]
        costume=arr[4]
        img=arr[9]
        # Remove leading/trailing whitespace
        gsub(/^ +| +$/, "", name)
        gsub(/^ +| +$/, "", form)
        gsub(/^ +| +$/, "", costume)
        # Use img as key to ensure uniqueness
        if (!seen[img]++) {
            print "{\"name\": \"" name "\", \"form\": \"" form "\", \"costume\": \"" costume "\", \"img\": \"" img "\"}"
        }
    }
' "$INPUT" | jq -s '.' > "$OUTPUT"

echo "Output written to $OUTPUT"