variable "branch" {
  description = "optional branch for use in the name"
  default = ""
}

variable "location" {
  description = "default location to use if not specified"
  default = "switzerlandnorth"  
}

variable "openai_embedding_models" {
  description = "list of embedding models to deploy"
  default = [{
    name     = "text-embedding-ada-002"
    version  = "2"
    capacity = 200
    }, {
    name    = "gpt-4"
    version = "turbo-2024-04-09"
    capacity = 150
  }]
  type = list(object({
    name     = string
    version  = optional(string, "1")
    capacity = optional(number, 1)
  }))

}