import unittest

from action_engine import analyze_business_action


class ActionEngineTests(unittest.TestCase):
    def test_clear_delivery_request_extracts_business_fields(self):
        result = analyze_business_action(
            "Abeg I want two bluetooth headphones. I need am delivered to Mokola tomorrow afternoon",
            asr_language="en", asr_confidence=90,
        )
        self.assertEqual(result["intent"], "DELIVERY_REQUEST")
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(result["product_or_service"], "Bluetooth Headphones")
        self.assertEqual(result["location"], "Mokola")
        self.assertEqual(result["date"], "Tomorrow")
        self.assertEqual(result["time"], "Afternoon")

    def test_ambiguous_amount_is_not_repeated_as_fact(self):
        result = analyze_business_action(
            "I have paid 15000 or 50000 naira", asr_confidence=95
        )
        self.assertIsNone(result["amount"])
        self.assertTrue(result["field_states"]["amount"]["requires_confirmation"])
        self.assertNotIn("₦15,000", result["suggested_reply"])
        self.assertNotIn("₦50,000", result["suggested_reply"])

    def test_conflicting_quantity_is_not_guessed(self):
        result = analyze_business_action(
            "I want two or three phones", asr_confidence=95
        )
        self.assertIsNone(result["quantity"])
        self.assertTrue(result["field_states"]["quantity"]["requires_confirmation"])

    def test_low_asr_confidence_pauses_extracted_critical_fields(self):
        result = analyze_business_action(
            "Deliver two phones to Mokola tomorrow", asr_confidence=20
        )
        self.assertTrue(result["needs_confirmation"])
        self.assertEqual(result["field_states"]["quantity"]["confidence"], "low")
        self.assertIn("Confirm", result["required_action"])

    def test_missing_required_product_is_exposed(self):
        result = analyze_business_action("How much?", asr_confidence=90)
        self.assertEqual(result["intent"], "PRICE_ENQUIRY")
        self.assertIn("Exact product or service", result["missing_information"])
        self.assertTrue(result["field_states"]["product_or_service"]["requires_confirmation"])

    def test_negative_payment_statement_is_not_reversed(self):
        result = analyze_business_action("I have not paid", asr_confidence=95)
        self.assertNotEqual(result["intent"], "PAYMENT_CONFIRMATION")
        self.assertIsNone(result["payment_status"])

    def test_out_of_scope_message_returns_safe_unknown(self):
        result = analyze_business_action("The weather is pleasant today", asr_confidence=95)
        self.assertEqual(result["intent"], "UNKNOWN")
        self.assertIn("clarify", result["suggested_reply"].lower())

    def test_payment_claim_is_never_verified_from_speech(self):
        result = analyze_business_action("I don pay 15000 naira", asr_confidence=95)
        self.assertEqual(result["intent"], "PAYMENT_CONFIRMATION")
        self.assertEqual(result["payment_status"], "Customer reports payment sent")
        self.assertTrue(result["field_states"]["payment_status"]["requires_confirmation"])
        self.assertIn("independently", result["required_action"].lower())


if __name__ == "__main__":
    unittest.main()
