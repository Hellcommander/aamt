--[[
@description JSON to Simple Binary Converter
Converts a JSON file into a very simple, custom binary-like format to speed up loading.
This is a simulation of using a format like MessagePack or FlatBuffers.

Format Markers:
- T: Table (map)
- A: Array
- S: String
- N: Number
- B: Boolean
- L: Nil
- E: End of Table/Array
]]

local M = {}

local function serialize(data)
  local serializedParts = {}

  local function doSerialize(value)
    local valueType = type(value)

    if valueType == "table" then
      -- Check if it's an array or a map
      local isArray = #value > 0 and value[1] ~= nil
      if isArray then
        table.insert(serializedParts, "A")
        for i = 1, #value do
          doSerialize(value[i])
        end
      else -- It's a map
        table.insert(serializedParts, "T")
        for k, v in pairs(value) do
          doSerialize(k) -- Serialize key
          doSerialize(v) -- Serialize value
        end
      end
      table.insert(serializedParts, "E") -- End of table marker
    elseif valueType == "string" then
      table.insert(serializedParts, "S")
      table.insert(serializedParts, string.format("%d", #value))
      table.insert(serializedParts, ":")
      table.insert(serializedParts, value)
    elseif valueType == "number" then
      table.insert(serializedParts, "N" .. tostring(value) .. "\0") -- Null-terminated number
    elseif valueType == "boolean" then
      table.insert(serializedParts, "B" .. (value and "1" or "0"))
    elseif valueType == "nil" then
      table.insert(serializedParts, "L")
    else
      sb.logWarn("jsonToBinary: Unsupported data type for serialization: " .. valueType)
      table.insert(serializedParts, "L") -- Serialize unsupported types as nil
    end
  end

  doSerialize(data)
  return table.concat(serializedParts)
end

function M.convert(inputJsonPath, outputBinaryPath)
  if not sb.fileExists(inputJsonPath) then
    sb.logError("jsonToBinary: Input JSON file not found: " .. inputJsonPath)
    return
  end

  local jsonData = sb.jsonFromFile(inputJsonPath)
  if not jsonData then
    sb.logError("jsonToBinary: Failed to parse input JSON: " .. inputJsonPath)
    return
  end

  sb.logInfo("Converting " .. inputJsonPath .. " to binary format.")
  local binaryData = serialize(jsonData)
  sb.fileWrite(outputBinaryPath, binaryData)
  sb.logInfo("Successfully wrote binary data to " .. outputBinaryPath)
end

return M
