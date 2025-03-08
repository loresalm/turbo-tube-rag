from DocumentProcessor import DocumentProcessor

########################################
#                                      #
#      Step1: article --> script       #
#                                      #
########################################
cofig_path = "data/inputs/config.json"
processor = DocumentProcessor(cofig_path)
# get fun facts from url
processor.get_fun_facts()

#processor.generate_queries_script(fact_id, output_file_path)
#processor.get_script_sentences(fact_id, video_sections)