# Festival Square
**Aliases:** festival square, the square, town square, festival grounds, the festival, festival plaza

## Description
A wide cobblestone plaza at the heart of Sandpoint, ringed by the cathedral, the stage, and the main commercial street. During the Swallowtail Festival every inch of usable space is taken: merchant tents in overlapping rows, temporary game lanes roped off along the eastern wall, the swallowtail release wagon parked near the centre, and a dense crowd flowing between all of it. The smell of fry-bread and roasting meat settles over the square from mid-morning. At the northern end the sage stage faces the cathedral across the open clearing.

## Typical Occupants
Sandpoint's full population plus several dozen out-of-town visitors during the festival. Mayor Deverin gave her address here this morning; Cyrdak Drokkus circulates along the market rows. Sheriff Hemlock passes through on patrol every thirty minutes. The tavern serving tables line the western edge — Ameiko Kaijitsu runs the Rusty Dragon station herself.

## Current State
Open and crowded. Alert level: none — festival security is light. The cobblestones are slippery in front of the serving tables where mead has already been spilled. Sightlines across the square are limited by the tent canopies; anyone wanting to observe the crowd unnoticed can do so from the stage steps or the narrow alley between the chandler's shop and the milliner.

## Zones

| id | name | description | visible | source | tags |
|----|------|-------------|---------|--------|------|
| cathedral_stairs | Cathedral Stairs | The raised steps before the new cathedral, exposed and easy to see from across the square. | yes | authored | higher_ground, sanctuary |
| alleyway | Alleyway | A narrow side lane between shops at the square's edge, good for sudden arrivals and quick exits. | yes | authored | escape_route, shadowed |
| well | Well | The stone well and open cobbles near it, with room to circle but little cover. | yes | authored | landmark |
| market_stalls | Market Stalls | Crowded rows of tents, tables, awnings, crates, and spilled festival goods. | yes | authored | cover, crowded |
| center | Center | The square's central clearing around the swallowtail wagon and main crowd flow. | yes | authored | open, crowded |

## Access Points

| id | from | to | label | state | bidirectional | requirements | description |
|----|------|----|-------|-------|---------------|--------------|-------------|
| cathedral_stairs_center | cathedral_stairs | center | Cathedral steps | open | yes | - | Broad stone steps lead down into the main square. |
| alleyway_center | alleyway | center | Alley mouth | open | yes | - | The side lane opens directly onto the central cobbles. |
| alleyway_well | alleyway | well | Narrow lane by the well | open | yes | - | The lane bends toward the well along the shopfronts. |
| well_market_stalls | well | market_stalls | Stall-side path | open | yes | - | A path between vendor ropes leads from the well into the stalls. |
| market_stalls_center | market_stalls | center | Market gap | open | yes | - | Gaps between tents open into the central clearing. |

<!-- REFERENCE -->
**District:** Central Sandpoint
**Type:** Civic / Gathering
**Associated NPCs:** Kendra Deverin (civic address), Cyrdak Drokkus (circulating), Belor Hemlock (patrol), Ameiko Kaijitsu (tavern station), Abstalar Zantus (cathedral plaza)
**Author Notes:** Primary location for Act I social phase. The cathedral_alarm event fires from here at sunset. The goblin raid opens in this square.
