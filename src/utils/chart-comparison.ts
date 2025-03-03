interface ChartData {
  planets: {
    name: string;
    sign: string;
    degree: number;
    house: number;
    longitude: number;
    retrograde?: boolean;
  }[];
  houses: {
    number: number;
    sign: string;
    degree: number;
  }[];
  ascendant: {
    sign: string;
    degree: number;
    longitude: number;
  };
  aspects?: {
    planet1: string;
    planet2: string;
    angle: number;
    type: string;
  }[];
}

type PlanetName = 'Sun' | 'Moon' | 'Mars' | 'Mercury' | 'Venus' | 'Jupiter' | 'Saturn';

interface Dignity {
  exaltation: string;
  debilitation: string;
  own: string[];
}

const dignities: Record<PlanetName, Dignity> = {
  Sun: { exaltation: 'Aries', debilitation: 'Libra', own: ['Leo'] },
  Moon: { exaltation: 'Taurus', debilitation: 'Scorpio', own: ['Cancer'] },
  Mars: { exaltation: 'Capricorn', debilitation: 'Cancer', own: ['Aries', 'Scorpio'] },
  Mercury: { exaltation: 'Virgo', debilitation: 'Pisces', own: ['Gemini', 'Virgo'] },
  Venus: { exaltation: 'Pisces', debilitation: 'Virgo', own: ['Taurus', 'Libra'] },
  Jupiter: { exaltation: 'Cancer', debilitation: 'Capricorn', own: ['Sagittarius', 'Pisces'] },
  Saturn: { exaltation: 'Libra', debilitation: 'Aries', own: ['Capricorn', 'Aquarius'] }
};

/**
 * Compare two chart data objects and return the differences
 * @param chart1 First chart data
 * @param chart2 Second chart data
 * @returns Object containing differences between the charts
 */
export function compareChartData(chart1: ChartData, chart2: ChartData) {
  const differences = {
    planets: [] as any[],
    houses: [] as any[],
    ascendant: null as any,
    aspects: [] as any[]
  };

  // Compare planets
  chart1.planets.forEach(planet1 => {
    const planet2 = chart2.planets.find(p => p.name === planet1.name);
    if (planet2) {
      if (
        planet1.sign !== planet2.sign ||
        Math.abs(planet1.degree - planet2.degree) > 0.1 ||
        planet1.house !== planet2.house
      ) {
        differences.planets.push({
          name: planet1.name,
          chart1: {
            sign: planet1.sign,
            degree: planet1.degree,
            house: planet1.house
          },
          chart2: {
            sign: planet2.sign,
            degree: planet2.degree,
            house: planet2.house
          }
        });
      }
    }
  });

  // Compare houses
  chart1.houses.forEach((house1, index) => {
    const house2 = chart2.houses[index];
    if (
      house1.sign !== house2.sign ||
      Math.abs(house1.degree - house2.degree) > 0.1
    ) {
      differences.houses.push({
        number: house1.number,
        chart1: {
          sign: house1.sign,
          degree: house1.degree
        },
        chart2: {
          sign: house2.sign,
          degree: house2.degree
        }
      });
    }
  });

  // Compare ascendant
  if (
    chart1.ascendant.sign !== chart2.ascendant.sign ||
    Math.abs(chart1.ascendant.degree - chart2.ascendant.degree) > 0.1
  ) {
    differences.ascendant = {
      chart1: {
        sign: chart1.ascendant.sign,
        degree: chart1.ascendant.degree
      },
      chart2: {
        sign: chart2.ascendant.sign,
        degree: chart2.ascendant.degree
      }
    };
  }

  // Compare aspects if they exist
  if (chart1.aspects && chart2.aspects) {
    const aspectsMap1 = new Map(
      chart1.aspects.map(aspect => [
        `${aspect.planet1}-${aspect.planet2}-${aspect.type}`,
        aspect
      ])
    );
    const aspectsMap2 = new Map(
      chart2.aspects.map(aspect => [
        `${aspect.planet1}-${aspect.planet2}-${aspect.type}`,
        aspect
      ])
    );

    // Find aspects in chart1 that are different or missing in chart2
    aspectsMap1.forEach((aspect1, key) => {
      const aspect2 = aspectsMap2.get(key);
      if (!aspect2 || Math.abs(aspect1.angle - aspect2.angle) > 0.1) {
        differences.aspects.push({
          planets: [aspect1.planet1, aspect1.planet2],
          type: aspect1.type,
          chart1: { angle: aspect1.angle },
          chart2: aspect2 ? { angle: aspect2.angle } : null
        });
      }
    });

    // Find aspects in chart2 that are missing in chart1
    aspectsMap2.forEach((aspect2, key) => {
      if (!aspectsMap1.has(key)) {
        differences.aspects.push({
          planets: [aspect2.planet1, aspect2.planet2],
          type: aspect2.type,
          chart1: null,
          chart2: { angle: aspect2.angle }
        });
      }
    });
  }

  return differences;
}

/**
 * Calculate the orb (difference in degrees) between two aspects
 * @param angle1 First angle in degrees
 * @param angle2 Second angle in degrees
 * @returns The orb in degrees
 */
export function calculateOrb(angle1: number, angle2: number): number {
  let diff = Math.abs(angle1 - angle2);
  if (diff > 180) {
    diff = 360 - diff;
  }
  return diff;
}

/**
 * Check if a planet is in its exaltation, debilitation, or own sign
 * @param planet Planet name
 * @param sign Current sign
 * @returns Object containing dignity information
 */
export function getPlanetaryDignity(planet: string, sign: string): { status: 'exalted' | 'debilitated' | 'own' | 'neutral' } {
  if (isPlanetName(planet)) {
    const dignity = dignities[planet];
    if (sign === dignity.exaltation) return { status: 'exalted' };
    if (sign === dignity.debilitation) return { status: 'debilitated' };
    if (dignity.own.includes(sign)) return { status: 'own' };
  }
  return { status: 'neutral' };
}

function isPlanetName(planet: string): planet is PlanetName {
  return planet in dignities;
}
