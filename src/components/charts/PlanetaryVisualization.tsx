// In the PlanetModel or Planet component, adjust rendering for Saturn
const renderPlanet = (planet: Planet) => {
  // Apply specific adjustment for Saturn to correct vertical alignment
  const adjustmentY = planet.name === "Saturn" ? -0.15 : 0; // Adjust the value as needed

  return (
    <PlanetModel
      key={planet.id}
      planet={planet}
      position={[
        planet.position.x,
        planet.position.y + adjustmentY, // Apply vertical adjustment for Saturn
        planet.position.z
      ]}
      rotation={planet.rotation}
      scale={planet.scale}
      onClick={handlePlanetClick}
      isSelected={selectedPlanet?.id === planet.id}
    />
  );
}
