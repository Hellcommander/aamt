--[[
@description JSON Chunking Tool
Splits a large JSON file (assumed to be an array of objects) into multiple smaller chunk files.

Usage (from a Lua script):
  local chunker = require("/scripts/tools/chunkJson.lua")
  chunker.chunkFile("/path/to/large.json", "/path/to/output_dir", 5)
]]

local M = {}

function M.chunkFile(inputPath, outputDir, numChunks)
  if not sb.fileExists(inputPath) then
    sb.logError("chunkJson: Input file not found: " .. inputPath)
    return false, "Input file not found"
  end

  local data = sb.jsonFromFile(inputPath)
  if type(data) ~= "table" or not data[1] then
    sb.logError("chunkJson: Input file must be a JSON array.")
    return false, "Input must be a JSON array"
  end

  local totalItems = #data
  if totalItems == 0 then
    sb.logWarn("chunkJson: Input file is empty.")
    return true
  end

  local itemsPerChunk = math.ceil(totalItems / numChunks)
  local baseName = inputPath:match("([^/]+)%.json$") or "chunk"

  sb.logInfo(string.format("Chunking %s into %d files with ~%d items each.", inputPath, numChunks, itemsPerChunk))

  for i = 1, numChunks do
    local startIndex = (i - 1) * itemsPerChunk + 1
    local endIndex = math.min(i * itemsPerChunk, totalItems)

    if startIndex > totalItems then break end

    local chunkData = {}
    for j = startIndex, endIndex do
      table.insert(chunkData, data[j])
    end

    local outputPath = string.format("%s/%s.part_%d.json", outputDir, baseName, i)
    sb.fileWrite(outputPath, sb.jsonFormat(chunkData))
    sb.logInfo("Wrote chunk: " .. outputPath)
  end

  return true
end

return M
