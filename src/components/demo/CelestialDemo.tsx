import React from 'react';
import { CelestialBody } from '../common/CelestialBody';
import { getRandomImageFromCategory } from '@/utils/imageLoader';

interface DemoOption {
  title: string;
  description: string;
  component: React.ReactNode;
}

export const CelestialDemo: React.FC = () => {
  // Define demo options to showcase different settings
  const demoOptions: DemoOption[] = [
    {
      title: 'Rotating Sun with Glow',
      description: 'Solar rotation with high-intensity orange glow effect',
      component: (
        <CelestialBody
          src={getRandomImageFromCategory('planets', 'sun')}
          alt="Rotating Sun"
          type="sun"
          rotate={true}
          rotationDuration={60}
          glow={true}
          glowIntensity="high"
          className="w-40 h-40"
        />
      )
    },
    {
      title: 'Pulsing Moon',
      description: 'Subtle pulsing effect simulating lunar energy',
      component: (
        <CelestialBody
          src="/images/planets/mercury/mercury-1.jpg" // Using Mercury as placeholder for Moon
          alt="Pulsing Moon"
          type="moon"
          pulseEffect={true}
          glow={true}
          className="w-40 h-40"
        />
      )
    },
    {
      title: 'Glowing Planet',
      description: 'Planet with atmospheric glow effect',
      component: (
        <CelestialBody
          src={getRandomImageFromCategory('planets', 'jupiter')}
          alt="Glowing Planet"
          type="planet"
          glow={true}
          className="w-40 h-40"
        />
      )
    },
    {
      title: 'Rotating Planet',
      description: 'Slowly rotating planet with subtle glow',
      component: (
        <CelestialBody
          src={getRandomImageFromCategory('planets', 'saturn')}
          alt="Rotating Planet"
          type="planet"
          rotate={true}
          rotationDuration={120}
          glow={true}
          glowIntensity="low"
          className="w-40 h-40"
        />
      )
    },
    {
      title: 'Nebula with Color Effect',
      description: 'Nebula with custom purple glow',
      component: (
        <CelestialBody
          src={getRandomImageFromCategory('nebulea')}
          alt="Glowing Nebula"
          type="nebula"
          glow={true}
          glowColor="rgba(180, 100, 255, 0.7)"
          className="w-40 h-40 rounded-lg"
        />
      )
    },
    {
      title: 'Pulsing Star',
      description: 'Star with twinkling pulse effect',
      component: (
        <CelestialBody
          src={getRandomImageFromCategory('backgrounds-2')}
          alt="Pulsing Star"
          type="star"
          pulseEffect={true}
          rotate={true}
          rotationDuration={180}
          glow={true}
          className="w-40 h-40"
        />
      )
    }
  ];

  return (
    <div className="py-12">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-white mb-8 text-center">Celestial Animation Showcase</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {demoOptions.map((demo, index) => (
            <div 
              key={index}
              className="bg-gradient-to-br from-slate-900/90 to-blue-900/20 backdrop-blur-sm rounded-xl 
                p-6 border border-blue-800/30 flex flex-col items-center"
            >
              <div className="mb-4">
                {demo.component}
              </div>
              <h3 className="text-xl font-semibold text-blue-300 mb-2 text-center">{demo.title}</h3>
              <p className="text-blue-200 text-sm text-center">{demo.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}; 