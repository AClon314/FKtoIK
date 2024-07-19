# FK to IK Blender addon
A Blender addon to bake FK movements to un-parented bone transform keyframes. This comes in handy especially when trying to retarget from motion capture rigs (where all motion is usually FK) to rigs that that have IK bone setups.

## Installation

1. Download the script file (`fktoikaddon.py`).
2. Open Blender and go to `Edit > Preferences`.
3. In the Preferences window, select the `Add-ons` tab.
4. Follow the step for your Blender version:
   | Blender Version | Installation |
   |-----------------|-------------------|
   | Blender 4.1-    | Click on the `Install...` button at the top. |
   | Blender 4.2+    | Click on the down arrow at the top-right, then click `Install from Disk...`. |
5. Navigate to the downloaded script file, select it, and click `Install Add-on`.
6. Enable the add-on by checking the checkbox next to `FK to IK Bone Conversion`.

## Usage

1. Open the `FK to IK` panel in the 3D Viewport's sidebar (press `N` to toggle the sidebar).
2. Set the armature by selecting it in the `Armature` field.
3. Add bones to the list by clicking the `+` button.
4. Select bones from the armature for each list item.
5. Deselect "Full timeline" and select your desired keyframes, or leave it on (on by default) to bake the full length of the timeline into keyframes.
6. Click the `Convert FK to IK` button to perform the conversion.

## How it works:

- Duplicates specified bones in an armature
- Adds "copy location" and "copy rotation" constraints to duplicated bones, so that they have the same transforms as the FK bones
- Bakes animation to keyframes for duplicate bones
- Clears parents of specified bones
- Adds the same copy transform constraints, but this time backwards, so the original bones have the same baked transforms as the duplicate bones
- Bakes animation to keyframes for original bones
- Clean up duplicated bones

## Contributing

If you find a bug or have a feature request, please open an issue on the [GitHub repository](https://github.com/Pinpoint24/FKtoIKaddon).

## TODO

- [ ] Add an option to add IK constraints that snap to the newly baked bones
- [ ] Maybe: Auto-generate pole bones for generated IK constraints

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
