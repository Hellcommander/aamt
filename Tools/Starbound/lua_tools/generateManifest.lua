--[[
@description Manifest Generator
Scans the mod directory to produce a manifest of all relevant files,
their types, and metadata. This manifest is used by the ModManager
for optimized progressive loading.
]]

local generator = {}

-- Configuration for file types and their corresponding directories
local fileTypeConfig = {
  { type = "lua_script", path = "scripts", extension = ".lua" },
  { type = "config", path = ".", extension = ".config" },
  { type = "json_config", path = ".", extension = ".json" },
  { type = "patch", path = ".", extension = ".patch" },
  { type = "image", path = "interface", extension = ".png" },
  { type = "gui", path = "interface", extension = ".gui" },
  -- Add other file types as needed
}

-- Recursively scans a directory for files matching the config
function generator.scanDirectory(path, modRoot)
  local files = {}
  for _, file in ipairs(sb.dirents(path)) do
    local fullPath = path .. "/" .. file
    if sb.isDirectory(fullPath) then
      local subFiles = generator.scanDirectory(fullPath, modRoot)
      for _, subFile in ipairs(subFiles) do
        table.insert(files, subFile)
      end
    else
      table.insert(files, fullPath:sub(#modRoot + 2)) -- Store relative path
    end
  end
  return files
end

-- Generates the manifest
function generator.generate()
  local manifest = {
    version = "1.0",
    generatedAt = os.time(),
    files = {}
  }

  local modRoot = sb.modRoot()

  for _, config in ipairs(fileTypeConfig) do
    local searchPath = modRoot .. "/" .. config.path
    if sb.dirents(searchPath) then
      local foundFiles = generator.scanDirectory(searchPath, modRoot)
      for _, file in ipairs(foundFiles) do
        if file:hasSuffix(config.extension) then
          table.insert(manifest.files, {
            path = file,
            type = config.type,
            size = sb.fileSize(modRoot .. "/" .. file)
          })
        end
      end
    end
  end

  -- Write the manifest to a file
  local manifestJson = sb.jsonFormat(manifest)
  sb.fileWrite(modRoot .. "/modManifest.json", manifestJson)

  sb.logInfo("Mod manifest generated successfully.")
end

return generator
