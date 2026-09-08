"""
plip_engine.py

Pont entre :
- XML PLIP
- analyse des résidus
- statistiques
- génération interaction 2D

Pas de visualisation 3D.
"""

from pathlib import Path
import xml.etree.ElementTree as ET


try:
    from src.plip_2d_diagram import generate
except Exception:
    generate = None




def parse_plip_xml(xml_file):

    import xml.etree.ElementTree as ET

    tree = ET.parse(xml_file)
    root = tree.getroot()

    residues = []
    interactions = []

    types = {

        "hydrophobic_interactions":
        "Hydrophobic",

        "hydrogen_bonds":
        "Hydrogen bond",

        "salt_bridges":
        "Salt bridge",

        "pi_stacks":
        "Pi stacking",

        "pi_cation_interactions":
        "Pi cation",

        "water_bridges":
        "Water bridge",

        "halogen_bonds":
        "Halogen bond"

    }


    for group,label in types.items():

        for item in root.findall(
            f".//{group}/*"
        ):

            data={
                "type":label
            }


            for child in item:

                data[
                    child.tag
                ] = child.text


            interactions.append(
                data
            )


            residues.append({

                "residue":
                    data.get(
                        "restype",
                        "?"
                    ),

                "chain":
                    data.get(
                        "reschain",
                        "?"
                    ),

                "position":
                    data.get(
                        "resnr",
                        "?"
                    ),

                "type":
                    label

            })


    return {

        "residues":
            residues,

        "interactions":
            interactions

    }


def generate_visualization(
    xml_file,
    complex_pdb=None
):

    result = parse_plip_xml(
        xml_file
    )


    stats = {

        "nombre_residus_reference":
            len(result["residues"]),

        "nombre_interactions":
            len(result["interactions"]),

    }



    image = None


    # génération diagramme 2D uniquement
    if generate and complex_pdb:

        try:

            output = Path(
                xml_file
            ).with_suffix(
                ".png"
            )

            image = generate(
                Path(xml_file),
                Path(complex_pdb),
                output
            )

        except Exception as e:

            print(
                "Erreur génération 2D:",
                e
            )



    result["statistics"] = stats

    result["image_2d"] = image


    return result
