--[[
@description Asset Packer Tool
Scans a directory and packs all its files into a single asset bundle.
The bundle has a JSON index at the beginning for fast lookups.

Format:
1. 4-byte number: Size of the JSON index.
2. JSON Index: A map of { "filePath": [offset, size] }.
3. Raw file data concatenated.
]]

local M = {}

-- Recursively scan a directory and return a flat list of file paths
local function findFiles(dir, baseDir)
  baseDir = baseDir or dir
  local fileList = {}
  local items = sb.dirents(dir)
  if not items then return {} end

  for _, item in ipairs(items) do
    local fullPath = dir .. "/" .. item
    if sb.isDirectory(fullPath) then
      local subFiles = findFiles(fullPath, baseDir)
      for _, subFile in ipairs(subFiles) do
        table.insert(fileList, subFile)
      end
    else
      -- Store path relative to the base directory
      table.insert(fileList, fullPath:sub(#baseDir + 2))
    end
  end
  return fileList
end

-- Packs a directory into a single archive file
function M.pack(inputDir, outputFile)
  sb.logInfo(string.format("Starting asset packing for directory: %s", inputDir))

  local files = findFiles(inputDir)
  if #files == 0 then
    sb.logWarn("No files found in directory to pack: " .. inputDir)
    return
  end

  local index = {}
  local currentOffset = 0
  local fileDataBlobs = {}

  -- First, build the index and prepare data blobs
  for _, relativePath in ipairs(files) do
    local fullPath = inputDir .. "/" .. relativePath
    local data
    if plugin and plugin.nativeMapper and plugin.nativeMapper.map then
      local h = plugin.nativeMapper.map(fullPath)
      if h then
        data = plugin.nativeMapper.read(h, 0, sb.fileSize(fullPath) or 0)
        plugin.nativeMapper.unmap(h)
      else
        sb.logWarn("assetPacker: nativeMapper failed to map file: " .. fullPath)
      end
    else
      data = sb.fileRead(fullPath, true) -- fallback
    end
    if data then
      local size = #data
      index[relativePath] = { offset = currentOffset, size = size }
      currentOffset = currentOffset + size
      table.insert(fileDataBlobs, data)
    else
      sb.logWarn("Could not read file for packing: " .. fullPath)
    end
  end

  -- Now, write everything to the output file
  local indexJson = sb.jsonFormat(index)
  local indexSize = #indexJson

  -- Write header (size of index) and the index itself
  -- NOTE: Starbound's file API doesn't support raw binary writes easily.
  -- This implementation will write string data. A C++ implementation would be better for performance.
  -- We'll simulate the binary structure with a string-based approach.
  local header = string.char(bit.band(bit.rshift(indexSize, 24), 0xFF))
               .. string.char(bit.band(bit.rshift(indexSize, 16), 0xFF))
               .. string.char(bit.band(bit.rshift(indexSize, 8), 0xFF))
               .. string.char(bit.band(indexSize, 0xFF))

  local finalContent = { header, indexJson }
  for _, blob in ipairs(fileDataBlobs) do
    table.insert(finalContent, blob)
  end

  sb.fileWrite(outputFile, table.concat(finalContent))
  sb.logInfo(string.format("Successfully packed %d files into %s", #files, outputFile))
end

return M
