
from pathlib import Path
import xml.etree.ElementTree as ET


class VisualizationManager:


    def __init__(self, output_dir="visualization_results"):

        self.output_dir = Path(output_dir)



    def scan(self):

        result = {

            "files": [],
            "xml": None,
            "images": [],
            "structures": [],
            "tables": []

        }


        if not self.output_dir.exists():

            return result



        for file in self.output_dir.rglob("*"):

            if not file.is_file():
                continue


            result["files"].append(str(file))


            ext = file.suffix.lower()


            if ext == ".xml":

                result["xml"] = str(file)


            elif ext in [".png",".jpg",".jpeg"]:

                result["images"].append(str(file))


            elif ext in [".pdb",".pdbqt",".sdf",".mol2"]:

                result["structures"].append(str(file))


            elif ext in [".csv",".json"]:

                result["tables"].append(str(file))


        return result



    def read_plip(self, xml):

        data = {

            "residues": [],
            "interactions": []

        }


        if not xml:
            return data


        path = Path(xml)


        if not path.exists():
            return data


        tree = ET.parse(path)

        root = tree.getroot()


        for r in root.findall(".//bs_residue"):

            data["residues"].append(
                r.attrib
            )


        for i in root.findall(".//interactions/*"):

            data["interactions"].append(

                {
                    "type": i.tag,
                    "data": i.attrib
                }

            )


        return data
