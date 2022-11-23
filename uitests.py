# ensure using <conda:lab> with Metashape.whl installed 
from easyams.utils import ImgLoaderPanel

if __name__ == "__main__":
    # test img loader panel
    ilp = ImgLoaderPanel()
    ilp.mainloop()