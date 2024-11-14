from matplotlib import pyplot as plt
import numpy as np
import seafreeze.seafreeze as sf

def phaselines(material_1, material_2):
    """
    v. 1.0 Clinton & Journaux, 2020
    Function calculates phase equilibria coordinates (K, MPa) based on the
    Gibbs energy of two materials.

    Example:
    >> phaselines('Ih', 'water1')
    """

    # Pressure and Temperature Structures for Extension
    PhaselinesD = {
        'Ih_water1': (np.arange(0.1, 300, 1), np.arange(239, 285, 0.5)),
        'Ih_II': (np.arange(0.1, 241, 1), np.arange(0.1, 269.5, 0.5)),
        'Ih_III': (np.arange(200, 216, 1), np.arange(230, 260.5, 0.5)),
        'II_III': (np.arange(100, 496, 1), np.arange(218.5, 258.7, 0.5)),
        'II_V': (np.arange(204, 808, 1), np.arange(164, 270.5, 0.5)),
        'II_VI': (np.arange(0.1, 900.1, 0.1), np.arange(0.1, 270.5, 0.5)),
        'III_V': (np.arange(340, 392), np.arange(210, 270.5, 0.5)),
        'III_water1': (np.arange(47, 491, 1), np.arange(240, 260.5, 0.5)),
        'V_water1': (np.arange(179, 726, 1), np.arange(239, 290.5, 0.5)),
        'V_VI': (np.arange(633, 685), np.arange(122, 297.5, 0.5)),
        'VI_water1': (np.arange(337, 2301, 1), np.arange(270, 375.5, 0.5))
    }

    # Data 'Ih' and 'water1'
    if ('Ih' == material_1 and 'water1' == material_2) or ('water1' == material_1 and 'Ih' == material_2):
        P = PhaselinesD['Ih_water1'][0]
        T = PhaselinesD['Ih_water1'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')
        P, T = np.meshgrid(P, T)

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'Ih')
        B = sf.getProp(PT, 'water1')
        Z = np.array(A.G) - np.array(B.G)
        
        return (P, T, Z.T)
    # Data for 'Ih' and 'II'
    elif ('Ih' == material_1 and 'II' == material_2) or ('II' == material_1 and 'Ih' == material_2):
        P = PhaselinesD['Ih_II'][0][::3]
        T = PhaselinesD['Ih_II'][1][::3]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'Ih')
        B = sf.getProp(PT, 'II')
        Z = np.array(A.G) - np.array(B.G)
        
        return (P, T, Z.T)
    # Data 'Ih' and 'III'
    elif('Ih' == material_1 and 'III' == material_2) or ('III' == material_1 and 'Ih' == material_2):
        P = PhaselinesD['Ih_III'][0]
        T = PhaselinesD['Ih_III'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'Ih')
        B = sf.getProp(PT, 'III')
        Z = np.array(A.G) - np.array(B.G)
        
        return (P, T, Z.T)
    # Data for 'II' and 'III'
    elif ('II' == material_1 and 'III' == material_2) or ('III' == material_1 and 'II' == material_2):
        P = PhaselinesD['II_III'][0]
        T = PhaselinesD['II_III'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'II')
        B = sf.getProp(PT, 'III')
        Z = np.array(A.G) - np.array(B.G)

        return (P, T, Z.T)
    # Data for 'II' and 'V'
    elif ('II' == material_1 and 'V' == material_2) or ('V' == material_1 and 'II' == material_2):
        P = PhaselinesD['II_V'][0]
        T = PhaselinesD['II_V'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'II')
        B = sf.getProp(PT, 'V')
        Z = np.array(A.G) - np.array(B.G)

        return (P, T, Z.T)
    # Data for 'II' and 'VI'
    elif ('II' == material_1 and 'VI' == material_2) or ('VI' == material_1 and 'II' == material_2):
        P = PhaselinesD['II_VI'][0][::4]
        T = PhaselinesD['II_VI'][1][::4]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'II')
        B = sf.getProp(PT, 'VI')
        Z = np.array(A.G) - np.array(B.G)

        return (P, T, Z.T)
    # Data for 'III' and 'V'
    elif ('III' == material_1 and 'V' == material_2) or ('V' == material_1 and 'III' == material_2):
        P = PhaselinesD['III_V'][0]
        T = PhaselinesD['III_V'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'III')
        B = sf.getProp(PT, 'V')
        Z = np.array(A.G) - np.array(B.G)
        return (P, T, Z.T)
    # Data for 'III' and 'water1'
    elif ('III' == material_1 and 'water1' == material_2) or ('water1' == material_1 and 'III' == material_2):
        P = PhaselinesD['III_water1'][0]
        T = PhaselinesD['III_water1'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'III')
        B = sf.getProp(PT, 'water1')
        Z = np.array(A.G) - np.array(B.G)
        return (P, T, Z.T)
    # Data for 'V' and 'water1'
    elif ('V' == material_1 and 'water1' == material_2) or ('water1' == material_1 and 'V' == material_2):
        P = PhaselinesD['V_water1'][0]
        T = PhaselinesD['V_water1'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'V')
        B = sf.getProp(PT, 'water1')
        Z = np.array(A.G) - np.array(B.G)
        return (P, T, Z.T)
    # Data for 'VI' and 'water1'
    elif ('VI' == material_1 and 'water1' == material_2) or ('water1' == material_1 and 'VI' == material_2):
        P = PhaselinesD['VI_water1'][0]
        T = PhaselinesD['VI_water1'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'VI')
        B = sf.getProp(PT, 'water1')
        Z = np.array(A.G) - np.array(B.G)
        return (P, T, Z.T)
    # Data for 'V' and 'VI'
    elif ('V' == material_1 and 'VI' == material_2) or ('VI' == material_1 and 'V' == material_2):
        P = PhaselinesD['V_VI'][0]
        T = PhaselinesD['V_VI'][1]
        
        # Create meshgrid for pressure and temperature
        PT = np.array([P, T], dtype='object')

        # Use seafreeze to calculate Gibbs free energy
        A = sf.getProp(PT, 'V')
        B = sf.getProp(PT, 'VI')
        Z = np.array(A.G) - np.array(B.G)
                
        return (P, T, Z.T)
    # Return
    else:
        return