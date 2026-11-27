from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from network import Network


class Accounting(unittest.TestCase):
    def test_redirect_bytes_and_transfers_distinguish_hosts_and_frame_limits(self):
        net=Network()
        net.request({"requestId":"1","request":{"url":"https://example.net/a"}})
        net.request({"requestId":"1","request":{"url":"https://www.example.net/b"},"redirectResponse":{"encodedDataLength":90}})
        net.request({"requestId":"2","request":{"url":"https://notexample.net/asset"}})
        net.complete({"requestId":"1","encodedDataLength":850})
        pending=net.result("example.net",0)
        self.assertEqual(pending["encoded_bytes"],940)
        self.assertEqual((pending["requests"],pending["finished"],pending["pending"]),(3,2,1))
        self.assertFalse(pending["all_observed_responses_finished"])
        self.assertEqual(pending["outside_hosts"],["notexample.net"])
        net.complete({"requestId":"2","encodedDataLength":45})
        self.assertTrue(net.result("example.net",0)["all_observed_responses_finished"])
        self.assertFalse(net.result("example.net",1)["all_observed_responses_finished"])
    def test_failure_and_non_http_resource_have_no_invented_bytes(self):
        net=Network()
        net.request({"requestId":"1","request":{"url":"data:text/plain,example"}})
        net.complete({"requestId":"1","encodedDataLength":35})
        net.request({"requestId":"2","request":{"url":"https://example.org/"}})
        net.failure({"requestId":"2"})
        result=net.result("example.org",0)
        self.assertEqual(result["encoded_bytes"],0)
        self.assertEqual((result["requests"],result["failed"]),(1,1))
        self.assertFalse(result["all_observed_responses_finished"])
