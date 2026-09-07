#pragma once

#include "MechTypes.hpp"
#include <vector>
#include <memory>
#include <string>

namespace MagiTech {
namespace Mechs {

// Enhanced MeshGenerator with procedural generation
class MeshGenerator {
public:
    static MeshHandle buildMechMesh(const MechParams& p);
    
    // Enhanced features
    static MeshHandle buildProceduralMesh(const MechParams& p, const ProceduralParams& proc);
    static MeshHandle buildModularMesh(const MechParams& p);
    static MeshHandle buildLODMesh(const MechParams& p, int lodLevel);
    
    // Primitive generation
    static MeshHandle createBox(const glm::vec3& size, const glm::mat4& transform = glm::mat4(1.0f));
    static MeshHandle createCylinder(float radius, float height, int segments = 16);
    static MeshHandle createSphere(float radius, int segments = 16);
    static MeshHandle createCapsule(float radius, float height, int segments = 16);
    
    // Advanced features
    static MeshHandle createArmorPlates(const MechParams& p);
    static MeshHandle createWeaponMounts(const MechParams& p);
    static MeshHandle createThrusters(const MechParams& p);
    static MeshHandle createSensors(const MechParams& p);
    
    // Optimization
    static void optimizeMesh(MeshHandle mesh);
    static void weldVertices(MeshHandle mesh, float threshold = 0.001f);
    static void computeNormals(MeshHandle mesh);
    static void computeTangents(MeshHandle mesh);
    
private:
    static glm::mat4 computeLimbTransform(int limbIndex, const MechParams& p);
    static glm::mat4 computeMountTransform(const std::string& mountType, const MechParams& p);
    static MeshHandle attachWeaponMount(const std::string& mountType, const MechParams& p);
};

// Enhanced TextureGenerator with procedural skin generation
class TextureGenerator {
public:
    static TextureHandle buildMechSkin(const MechParams& p);
    
    // Enhanced features
    static TextureHandle buildProceduralSkin(const MechParams& p, const ProceduralParams& proc);
    static TextureHandle buildPatternTexture(const std::string& pattern, const MechParams& p);
    static TextureHandle buildNormalMap(const MechParams& p);
    static TextureHandle buildRoughnessMap(const MechParams& p);
    static TextureHandle buildMetallicMap(const MechParams& p);
    static TextureHandle buildEmissiveMap(const MechParams& p);
    
    // Pattern generation
    static void generateHexPattern(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    static void generateCamouflagePattern(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    static void generateTechPattern(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    static void generateDamagedPattern(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    
    // Noise generation
    static float generateNoise(float x, float y, const ProceduralParams& proc);
    static float generateFractalNoise(float x, float y, const ProceduralParams& proc);
    static float generateTurbulence(float x, float y, const ProceduralParams& proc);
    
    // Color manipulation
    static glm::vec3 blendColors(const glm::vec3& color1, const glm::vec3& color2, float factor);
    static glm::vec3 adjustBrightness(const glm::vec3& color, float factor);
    static glm::vec3 adjustContrast(const glm::vec3& color, float factor);
    static glm::vec3 adjustSaturation(const glm::vec3& color, float factor);
    
private:
    static void applyPatternOverlay(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    static void applyWearAndTear(std::vector<unsigned char>& pixels, int width, int height, const ProceduralParams& proc);
    static void applyEmissiveEffects(std::vector<unsigned char>& pixels, int width, int height, const MechParams& p);
};

// Enhanced SkeletonGenerator with multi-form rigging
class SkeletonGenerator {
public:
    static SkeletonHandle buildRig(const MechParams& p);
    
    // Enhanced features
    static SkeletonHandle buildMultiFormRig(const MechParams& p);
    static SkeletonHandle buildIKRig(const MechParams& p);
    static SkeletonHandle buildPhysicsRig(const MechParams& p);
    
    // Animation generation
    static AnimationHandle createIdleAnimation(const MechParams& p);
    static AnimationHandle createWalkAnimation(const MechParams& p);
    static AnimationHandle createRunAnimation(const MechParams& p);
    static AnimationHandle createJumpAnimation(const MechParams& p);
    static AnimationHandle createMorphAnimation(const MechParams& p, const std::string& fromForm, const std::string& toForm);
    
    // Form-specific animations
    static AnimationHandle createFormAnimation(const MechParams& p, const std::string& formName);
    static AnimationHandle createCombatAnimation(const MechParams& p);
    static AnimationHandle createFlightAnimation(const MechParams& p);
    static AnimationHandle createSwimAnimation(const MechParams& p);
    
    // Advanced rigging
    static void addIKChains(SkeletonHandle skeleton, const MechParams& p);
    static void addPhysicsConstraints(SkeletonHandle skeleton, const MechParams& p);
    static void addMorphTargets(SkeletonHandle skeleton, const MechParams& p);
    static void addBlendShapes(SkeletonHandle skeleton, const MechParams& p);
    
private:
    static glm::mat4 limbPose(int limbIndex, const MechParams& p);
    static glm::mat4 localTransformFor(const std::string& formName, const MechParams& p);
    static void setupAnimationClips(SkeletonHandle skeleton, const MechParams& p);
    static void setupMorphWeights(SkeletonHandle skeleton, const MechParams& p);
};

// Material generator for PBR materials
class MaterialGenerator {
public:
    static MaterialHandle buildMechMaterial(const MechParams& p);
    
    // Material types
    static MaterialHandle createMetallicMaterial(const MechParams& p);
    static MaterialHandle createRoughMaterial(const MechParams& p);
    static MaterialHandle createEmissiveMaterial(const MechParams& p);
    static MaterialHandle createTransparentMaterial(const MechParams& p);
    
    // Material properties
    static void setAlbedo(MaterialHandle material, const glm::vec3& color);
    static void setMetallic(MaterialHandle material, float value);
    static void setRoughness(MaterialHandle material, float value);
    static void setEmissive(MaterialHandle material, const glm::vec3& color, float intensity);
    static void setNormalStrength(MaterialHandle material, float strength);
    
private:
    static MaterialHandle createMaterialFromTextures(const MechParams& p, TextureHandle albedo, TextureHandle normal, 
                                                   TextureHandle roughness, TextureHandle metallic, TextureHandle emissive);
};

// Physics generator for collision and rigid bodies
class PhysicsGenerator {
public:
    static void generateCollisionMesh(const MechParams& p, std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    static void generateRigidBody(const MechParams& p, float& mass, glm::vec3& centerOfMass, glm::mat3& inertia);
    
    // Collision shapes
    static void generateCapsuleCollision(const MechParams& p, std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    static void generateBoxCollision(const MechParams& p, std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    static void generateConvexHullCollision(const MechParams& p, std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    
    // Joint constraints
    static void generateJointConstraints(const MechParams& p, std::vector<std::string>& jointNames, 
                                       std::vector<glm::vec3>& jointPositions, std::vector<glm::vec3>& jointAxes);
    
private:
    static glm::vec3 computeCenterOfMass(const MechParams& p);
    static glm::mat3 computeInertiaTensor(const MechParams& p, const glm::vec3& centerOfMass);
};

// LOD generator for performance optimization
class LODGenerator {
public:
    static MeshHandle generateLODMesh(MeshHandle originalMesh, int lodLevel, const MechParams& p);
    static void generateLODChain(const MechParams& p, std::vector<MeshHandle>& lodMeshes);
    
    // LOD optimization
    static void decimateMesh(MeshHandle mesh, float ratio);
    static void simplifyMesh(MeshHandle mesh, int targetTriangles);
    static void optimizeLOD(MeshHandle mesh, int lodLevel);
    
private:
    static float computeLODDistance(int lodLevel, const MechParams& p);
    static int computeLODTriangleCount(int lodLevel, const MechParams& p);
};

// === SEGMENTED MECH GENERATORS ===

// Segmented Mesh Generator for Snake/Worm Mechs
class SegmentedMeshGenerator {
public:
    static MeshHandle buildSegmentedMech(const SegmentedMechParams& p);
    
    // Segment generation
    static MeshHandle createSegment(const SegmentedMechParams& p, int segmentIndex);
    static MeshHandle createSegmentConnector(const SegmentedMechParams& p, int segmentIndex);
    static MeshHandle createArmorPlates(const SegmentedMechParams& p, int segmentIndex);
    static MeshHandle createEmissiveStrips(const SegmentedMechParams& p, int segmentIndex);
    
    // Assembly
    static MeshHandle assembleSegments(const std::vector<MeshHandle>& segments, const SegmentedMechParams& p);
    static MeshHandle applyTapering(MeshHandle mesh, const SegmentedMechParams& p);
    static MeshHandle addNoiseDetail(MeshHandle mesh, const SegmentedMechParams& p);
    
    // Primitive generation for segments
    static MeshHandle createCylinderSegment(float radius, float length, int segments = 16);
    static MeshHandle createHexagonSegment(float radius, float length);
    static MeshHandle createCustomSegment(const std::string& shape, float radius, float length);
    
private:
    static glm::mat4 computeSegmentTransform(int segmentIndex, const SegmentedMechParams& p);
    static glm::mat4 computeConnectorTransform(int segmentIndex, const SegmentedMechParams& p);
    static void applySegmentNoise(MeshHandle mesh, float noiseDetail);
};

// Segmented Texture Generator
class SegmentedTextureGenerator {
public:
    static TextureHandle buildSegmentedSkin(const SegmentedMechParams& p);
    
    // Pattern generation
    static TextureHandle buildSegmentPattern(const SegmentedMechParams& p);
    static TextureHandle buildArmorTexture(const SegmentedMechParams& p);
    static TextureHandle buildEmissiveTexture(const SegmentedMechParams& p);
    static TextureHandle buildNormalMap(const SegmentedMechParams& p);
    static TextureHandle buildRoughnessMap(const SegmentedMechParams& p);
    static TextureHandle buildMetallicMap(const SegmentedMechParams& p);
    
    // Procedural patterns
    static void generateHexPattern(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
    static void generateTechPattern(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
    static void generateDamagedPattern(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
    static void generateEmissiveStrips(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
    
private:
    static void applyWearAndTear(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
    static void applyEmissiveEffects(std::vector<unsigned char>& pixels, int width, int height, const SegmentedMechParams& p);
};

// Segmented Skeleton Generator
class SegmentedSkeletonGenerator {
public:
    static SkeletonHandle buildSegmentedRig(const SegmentedMechParams& p);
    
    // Bone chain generation
    static void createSegmentBones(SkeletonHandle skeleton, const SegmentedMechParams& p);
    static void createJointConstraints(SkeletonHandle skeleton, const SegmentedMechParams& p);
    static void createCockpitBone(SkeletonHandle skeleton, const SegmentedMechParams& p);
    
    // Animation generation
    static AnimationHandle createSlitherAnimation(const SegmentedMechParams& p);
    static AnimationHandle createCoilAnimation(const SegmentedMechParams& p);
    static AnimationHandle createUndulateAnimation(const SegmentedMechParams& p);
    static AnimationHandle createCustomAnimation(const SegmentedMechParams& p, const std::string& profile);
    
    // Procedural animation
    static AnimationHandle createWaveAnimation(const SegmentedMechParams& p, float amplitude, float frequency);
    static AnimationHandle createIKAnimation(const SegmentedMechParams& p, const glm::vec3& target);
    
private:
    static glm::mat4 computeBoneTransform(int boneIndex, const SegmentedMechParams& p);
    static void setupJointLimits(SkeletonHandle skeleton, int boneIndex, const SegmentedMechParams& p);
    static void setupCockpitAttachment(SkeletonHandle skeleton, const SegmentedMechParams& p);
};

// Segmented Physics Generator
class SegmentedPhysicsGenerator {
public:
    static PhysicsHandle buildSegmentedPhysics(const SegmentedMechParams& p);
    
    // Segment physics
    static PhysicsHandle createSegmentPhysics(const SegmentedMechParams& p, int segmentIndex);
    static void createJointPhysics(const SegmentedMechParams& p, int segmentIndex);
    static void createCockpitPhysics(const SegmentedMechParams& p);
    
    // Collision generation
    static void generateSegmentCollision(const SegmentedMechParams& p, int segmentIndex, 
                                       std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    static void generateConnectorCollision(const SegmentedMechParams& p, int segmentIndex,
                                         std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices);
    
private:
    static float computeSegmentMass(const SegmentedMechParams& p, int segmentIndex);
    static glm::vec3 computeSegmentCenterOfMass(const SegmentedMechParams& p, int segmentIndex);
    static glm::mat3 computeSegmentInertia(const SegmentedMechParams& p, int segmentIndex);
};

// Particle Generator for Segmented Mechs
class SegmentedParticleGenerator {
public:
    static ParticleHandle buildJointSparks(const SegmentedMechParams& p);
    static ParticleHandle buildExhaustEffects(const SegmentedMechParams& p);
    static ParticleHandle buildEmissiveParticles(const SegmentedMechParams& p);
    
    // Particle systems
    static ParticleHandle createSparkEmitter(const SegmentedMechParams& p, int jointIndex);
    static ParticleHandle createExhaustEmitter(const SegmentedMechParams& p, int segmentIndex);
    static ParticleHandle createEmissiveEmitter(const SegmentedMechParams& p, int segmentIndex);
    
private:
    static void configureSparkParticles(ParticleHandle emitter, const SegmentedMechParams& p);
    static void configureExhaustParticles(ParticleHandle emitter, const SegmentedMechParams& p);
    static void configureEmissiveParticles(ParticleHandle emitter, const SegmentedMechParams& p);
};

// Cockpit Generator
class CockpitGenerator {
public:
    static MeshHandle buildCockpit(const CockpitParams& p);
    static TextureHandle buildCockpitTexture(const CockpitParams& p);
    static MaterialHandle buildCockpitMaterial(const CockpitParams& p);
    
    // Cockpit components
    static MeshHandle createSeat(const CockpitParams& p);
    static MeshHandle createCanopy(const CockpitParams& p);
    static MeshHandle createConsole(const CockpitParams& p);
    static MeshHandle createControls(const CockpitParams& p);
    static MeshHandle createInstruments(const CockpitParams& p);
    
    // Glass and materials
    static MaterialHandle createGlassMaterial(const CockpitParams& p);
    static MaterialHandle createSeatMaterial(const CockpitParams& p);
    static MaterialHandle createConsoleMaterial(const CockpitParams& p);
    
private:
    static glm::mat4 computeSeatTransform(const CockpitParams& p);
    static glm::mat4 computeCanopyTransform(const CockpitParams& p);
    static glm::mat4 computeConsoleTransform(const CockpitParams& p);
    static glm::mat4 computeControlTransform(const CockpitParams& p, int controlIndex);
};

// UI Icon Generator
class UIIconGenerator {
public:
    static TextureHandle buildMechIcon(const SegmentedMechParams& p, const UIParams& ui);
    
    // Icon components
    static void drawMechSilhouette(std::vector<unsigned char>& pixels, int width, int height, 
                                  const SegmentedMechParams& p);
    static void drawBackground(std::vector<unsigned char>& pixels, int width, int height, 
                             const UIParams& ui);
    static void drawBorder(std::vector<unsigned char>& pixels, int width, int height, 
                          const UIParams& ui);
    static void addFlashEffect(std::vector<unsigned char>& pixels, int width, int height, 
                              const UIParams& ui);
    
private:
    static void generateSilhouettePoints(const SegmentedMechParams& p, std::vector<glm::vec2>& points);
    static void drawPolyline(std::vector<unsigned char>& pixels, int width, int height,
                            const std::vector<glm::vec2>& points, const glm::vec4& color);
};

// === CENTIPEDE MECH GENERATORS ===

// Centipede Segment Generator
class CentipedeSegmentGenerator {
public:
    static std::vector<MeshHandle> buildSegments(const CentipedeMechParams& p);
    static MeshHandle createSegment(const CentipedeMechParams& p, int segmentIndex);
    static MeshHandle createSegmentWithBevel(const CentipedeMechParams& p, int segmentIndex);
    static MeshHandle createSegmentWithArmor(const CentipedeMechParams& p, int segmentIndex);
    
    // Segment assembly
    static std::vector<MeshHandle> assembleSegments(const std::vector<MeshHandle>& segments, const CentipedeMechParams& p);
    static MeshHandle applySeamlessJoints(const std::vector<MeshHandle>& segments, const CentipedeMechParams& p);
    static MeshHandle addSegmentDetails(const MeshHandle& segment, const CentipedeMechParams& p, int segmentIndex);
    
private:
    static glm::mat4 computeSegmentTransform(int segmentIndex, const CentipedeMechParams& p);
    static void applySegmentColor(MeshHandle mesh, const glm::vec4& color);
    static void addSegmentArmor(MeshHandle mesh, const CentipedeMechParams& p, int segmentIndex);
};

// Centipede Joint Generator
class CentipedeJointGenerator {
public:
    static std::vector<MeshHandle> buildJoints(const CentipedeMechParams& p);
    static MeshHandle createJoint(const CentipedeMechParams& p, int jointIndex);
    static MeshHandle createBallJoint(const CentipedeMechParams& p, int jointIndex);
    static MeshHandle createHingeJoint(const CentipedeMechParams& p, int jointIndex);
    
    // Joint constraints
    static void setupJointConstraints(const std::vector<MeshHandle>& joints, const CentipedeMechParams& p);
    static void setupBallJointLimits(const CentipedeMechParams& p, int jointIndex);
    static void setupHingeJointLimits(const CentipedeMechParams& p, int jointIndex);
    
private:
    static glm::mat4 computeJointTransform(int jointIndex, const CentipedeMechParams& p);
    static float computeJointRadius(const CentipedeMechParams& p, int jointIndex);
};

// Centipede Leg Generator
class CentipedeLegGenerator {
public:
    static std::vector<MeshHandle> buildAllLegs(const CentipedeMechParams& p);
    static MeshHandle buildSingleLeg(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    
    // Leg components
    static MeshHandle createUpperLeg(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static MeshHandle createLowerLeg(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static MeshHandle createLegJoint(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static MeshHandle createFoot(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static MeshHandle createArmorPlate(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    
    // Leg assembly
    static MeshHandle assembleLeg(const std::vector<MeshHandle>& components, const CentipedeMechParams& p);
    static void setupLegIK(const MeshHandle& leg, const CentipedeMechParams& p, int segmentIndex, int legIndex);
    
private:
    static glm::mat4 computeLegTransform(int segmentIndex, int legIndex, const CentipedeMechParams& p);
    static glm::mat4 computeUpperLegTransform(int segmentIndex, int legIndex, const CentipedeMechParams& p);
    static glm::mat4 computeLowerLegTransform(int segmentIndex, int legIndex, const CentipedeMechParams& p);
    static glm::mat4 computeFootTransform(int segmentIndex, int legIndex, const CentipedeMechParams& p);
    static MeshHandle createFootByType(const std::string& footType, const CentipedeMechParams& p);
};

// Centipede Cockpit Generator
class CentipedeCockpitGenerator {
public:
    static MeshHandle buildCockpit(const CentipedeMechParams& p);
    static MeshHandle createCockpitInterior(const CentipedeMechParams& p);
    static MeshHandle createCockpitDisplays(const CentipedeMechParams& p);
    static MeshHandle createCockpitSeat(const CentipedeMechParams& p);
    static MeshHandle createCockpitControls(const CentipedeMechParams& p);
    
    // Cockpit components
    static MeshHandle createDisplayPanel(const CentipedeMechParams& p, int displayIndex);
    static MeshHandle createControlPanel(const CentipedeMechParams& p, const std::string& controlStyle);
    static MeshHandle createHolographicHUD(const CentipedeMechParams& p);
    static MeshHandle createCockpitWalls(const CentipedeMechParams& p);
    
private:
    static glm::mat4 computeCockpitTransform(const CentipedeMechParams& p);
    static glm::mat4 computeDisplayTransform(const CentipedeMechParams& p, int displayIndex);
    static glm::mat4 computeControlTransform(const CentipedeMechParams& p, const std::string& controlStyle);
    static MaterialHandle createCockpitMaterial(const CentipedeMechParams& p);
};

// Centipede Weapon Generator
class CentipedeWeaponGenerator {
public:
    static std::vector<MeshHandle> buildWeapons(const CentipedeMechParams& p);
    static MeshHandle createMissileTube(const CentipedeMechParams& p, int tubeIndex);
    static MeshHandle createAutocannon(const CentipedeMechParams& p, int slotIndex);
    static MeshHandle createTurret(const CentipedeMechParams& p);
    
    // Weapon components
    static MeshHandle createWeaponMount(const CentipedeMechParams& p, int hardpointIndex);
    static MeshHandle createWeaponBarrel(const CentipedeMechParams& p, const std::string& weaponType);
    static MeshHandle createWeaponAmmo(const CentipedeMechParams& p, const std::string& weaponType);
    
private:
    static glm::mat4 computeWeaponTransform(const CentipedeMechParams& p, int hardpointIndex);
    static glm::mat4 computeTurretTransform(const CentipedeMechParams& p);
    static MaterialHandle createWeaponMaterial(const CentipedeMechParams& p, const std::string& weaponType);
};

// Centipede Sensor Generator
class CentipedeSensorGenerator {
public:
    static MeshHandle buildSensorArray(const CentipedeMechParams& p);
    static MeshHandle createRadarArray(const CentipedeMechParams& p);
    static MeshHandle createSensorDish(const CentipedeMechParams& p);
    static MeshHandle createSensorAntenna(const CentipedeMechParams& p);
    
    // Sensor components
    static MeshHandle createRadarDish(const CentipedeMechParams& p);
    static MeshHandle createSensorMount(const CentipedeMechParams& p);
    static MeshHandle createSensorCable(const CentipedeMechParams& p);
    
private:
    static glm::mat4 computeSensorTransform(const CentipedeMechParams& p);
    static glm::mat4 computeRadarTransform(const CentipedeMechParams& p);
    static MaterialHandle createSensorMaterial(const CentipedeMechParams& p);
};

// Centipede Material Generator
class CentipedeMaterialGenerator {
public:
    static std::vector<MaterialHandle> assignMechMaterials(const CentipedeMechParams& p);
    static MaterialHandle createHullMaterial(const CentipedeMechParams& p);
    static MaterialHandle createJointMaterial(const CentipedeMechParams& p);
    static MaterialHandle createLegMaterial(const CentipedeMechParams& p);
    static MaterialHandle createCockpitMaterial(const CentipedeMechParams& p);
    static MaterialHandle createWeaponMaterial(const CentipedeMechParams& p);
    static MaterialHandle createSensorMaterial(const CentipedeMechParams& p);
    
private:
    static MaterialHandle createMaterialFromColor(const glm::vec4& color, float metallic, float roughness);
    static MaterialHandle createMaterialFromTexture(const std::string& texturePath, float metallic, float roughness);
};

// Centipede VFX Generator
class CentipedeVFXGenerator {
public:
    static std::vector<ParticleHandle> buildDamageAndThrusterFX(const CentipedeMechParams& p);
    static ParticleHandle createThrusterFX(const CentipedeMechParams& p, int segmentIndex);
    static ParticleHandle createDamageSparks(const CentipedeMechParams& p);
    static ParticleHandle createLegImpactFX(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    
    // VFX components
    static ParticleHandle createJetTrail(float intensity);
    static ParticleHandle createSparkSystem(int sparkCount);
    static ParticleHandle createImpactDust(const glm::vec3& position);
    
private:
    static void configureThrusterParticles(ParticleHandle emitter, float intensity);
    static void configureSparkParticles(ParticleHandle emitter, int count);
    static void configureImpactParticles(ParticleHandle emitter, const glm::vec3& position);
};

// Centipede Audio Generator
class CentipedeAudioGenerator {
public:
    static std::vector<AudioHandle> buildMechSounds(const CentipedeMechParams& p);
    static AudioHandle createStepSounds(const CentipedeMechParams& p);
    static AudioHandle createJointCreaks(const CentipedeMechParams& p);
    static AudioHandle createCockpitHum(const CentipedeMechParams& p);
    static AudioHandle createWeaponFire(const CentipedeMechParams& p);
    
    // Audio components
    static AudioHandle createWalkCycle(float frequency);
    static AudioHandle createAmbientCreak(float volume);
    static AudioHandle createCockpitAmbience(float volume);
    static AudioHandle createWeaponSound(const std::string& weaponType);
    
private:
    static void configureStepAudio(AudioHandle audio, float frequency);
    static void configureCreakAudio(AudioHandle audio, float volume);
    static void configureCockpitAudio(AudioHandle audio, float volume);
    static void configureWeaponAudio(AudioHandle audio, const std::string& weaponType);
};

// Centipede Collision Generator
class CentipedeCollisionGenerator {
public:
    static PhysicsHandle buildMechCollider(const CentipedeMechParams& p);
    static PhysicsHandle createSegmentCollider(const CentipedeMechParams& p, int segmentIndex);
    static PhysicsHandle createLegCollider(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static PhysicsHandle createCockpitCollider(const CentipedeMechParams& p);
    
    // Collision components
    static PhysicsHandle createCapsuleCollider(float radius, float length);
    static PhysicsHandle createBoxCollider(const glm::vec3& size);
    static PhysicsHandle createCompoundCollider(const std::vector<PhysicsHandle>& colliders);
    
private:
    static glm::mat4 computeSegmentColliderTransform(int segmentIndex, const CentipedeMechParams& p);
    static glm::mat4 computeLegColliderTransform(int segmentIndex, int legIndex, const CentipedeMechParams& p);
    static glm::mat4 computeCockpitColliderTransform(const CentipedeMechParams& p);
};

// Centipede Simulation Generator
class CentipedeSimulationGenerator {
public:
    static void setupJointSimulation(const std::vector<MeshHandle>& joints, const CentipedeMechParams& p);
    static void setupLegIKSimulation(const std::vector<MeshHandle>& legs, const CentipedeMechParams& p);
    static void setupMechPhysics(const CentipedeMechParams& p);
    static void setupControlSimulation(const CentipedeMechParams& p);
    
    // Simulation components
    static void setupHingeJoint(int jointIndex, float minAngle, float maxAngle, float torque);
    static void setupBallJoint(int jointIndex, float swingLimit, float twistLimit);
    static void setupLegIK(int legIndex, const glm::vec3& target, float chainLength);
    static void setupMassDistribution(const CentipedeMechParams& p);
    
private:
    static float computeJointTorque(const CentipedeMechParams& p, int jointIndex);
    static glm::vec3 computeLegTarget(const CentipedeMechParams& p, int segmentIndex, int legIndex);
    static float computeChainLength(const CentipedeMechParams& p, int legIndex);
    static glm::vec3 computeMassCenter(const CentipedeMechParams& p);
};

} // namespace Mechs
} // namespace MagiTech
